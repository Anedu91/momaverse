"""
Web crawling module for the event processing pipeline.

Uses Crawl4AI to crawl event websites and store content in the database.
"""

import asyncio
import json
import re
from datetime import datetime, timedelta

import httpx
from crawl4ai import CacheMode
import db

# Default timeout for crawl operations (in seconds)
DEFAULT_CRAWL_TIMEOUT = 180

# Minimum content size (in bytes) to consider a crawl successful.
# Crawls with less content than this are likely failed (e.g., JS-rendered
# pages that didn't load properly) and should be marked as failed.
MIN_CRAWL_CONTENT_SIZE = 500

try:
    from crawl4ai import BrowserConfig, CrawlerRunConfig
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    from crawl4ai.content_filter_strategy import PruningContentFilter
    from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
    from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter
except ImportError:
    print("Error: crawl4ai is required.")
    print("Install it with: pip install crawl4ai")
    raise


def strip_jsonp(text, callback_name=None):
    """Strip JSONP callback wrapper to get pure JSON string.

    If callback_name provided, strip that exact prefix.
    Otherwise use generic regex for any callback function name.
    Returns text unchanged if neither matches (already plain JSON).
    """
    text = text.strip()
    if callback_name:
        prefix = callback_name + '('
        if text.startswith(prefix):
            text = text[len(prefix):]
            # Remove trailing );
            text = text.rstrip(';').rstrip()
            if text.endswith(')'):
                text = text[:-1]
            return text
    # Generic JSONP pattern
    match = re.match(r'^[a-zA-Z_]\w*\s*\((.*)\)\s*;?\s*$', text, re.DOTALL)
    if match:
        return match.group(1)
    return text


def filter_by_date_window(events_dict, days_ahead=30):
    """Filter events dict (keyed by event ID) to only those with upcoming dates.

    Keeps events that have at least one proxima_fecha within the date window,
    or events with NO proxima_fecha at all (let Gemini decide relevance).
    Only excludes events whose ALL dates are past or beyond the window.
    """
    now = datetime.now()
    window_end = now + timedelta(days=days_ahead)
    filtered = {}

    for event_id, event in events_dict.items():
        dates_found = []

        # Navigate: event > lugares > * > funciones > * > proxima_fecha
        lugares = event.get('lugares', {})
        if isinstance(lugares, dict):
            for lugar_id, lugar in lugares.items():
                funciones = lugar.get('funciones', {})
                if isinstance(funciones, dict):
                    for func_id, funcion in funciones.items():
                        proxima = funcion.get('proxima_fecha')
                        if proxima:
                            try:
                                dt = datetime.strptime(proxima, '%Y-%m-%d %H:%M')
                                dates_found.append(dt)
                            except (ValueError, TypeError):
                                pass

        if not dates_found:
            # No dates found -- include (let Gemini decide)
            filtered[event_id] = event
        elif any(now <= dt <= window_end for dt in dates_found):
            # At least one date within window
            filtered[event_id] = event
        # else: all dates are past or beyond window -- exclude

    return filtered


def flatten_events_to_markdown(events_dict, fields_include=None):
    """Convert filtered JSON events dict to markdown for Gemini extraction.

    For each event produces:
    - Title, tags, venues with addresses, show times, URL, tickets link
    - Blank line between events
    """
    lines = []

    for event_id, event in events_dict.items():
        titulo = event.get('titulo', f'Event {event_id}')
        lines.append(f'## {titulo}')

        # Tags from clasificaciones
        clasificaciones = event.get('clasificaciones', {})
        if isinstance(clasificaciones, dict):
            tag_names = [c.get('descripcion', '') for c in clasificaciones.values() if c.get('descripcion')]
            if tag_names:
                lines.append(f'**Tags:** {", ".join(tag_names)}')

        # Venues and showtimes
        lugares = event.get('lugares', {})
        if isinstance(lugares, dict):
            for lugar_id, lugar in lugares.items():
                nombre = lugar.get('nombre', '')
                direccion = lugar.get('direccion', '')
                zona = lugar.get('zona', '')
                if nombre:
                    lines.append(f'**Venue:** {nombre}')
                addr_parts = [p for p in [direccion, zona] if p]
                if addr_parts:
                    lines.append(f'**Address:** {", ".join(addr_parts)}')

                funciones = lugar.get('funciones', {})
                if isinstance(funciones, dict):
                    for func_id, funcion in funciones.items():
                        dia = funcion.get('dia', '')
                        hora = funcion.get('hora', '')
                        proxima = funcion.get('proxima_fecha', '')
                        parts = [p for p in [dia, hora] if p]
                        time_str = ' '.join(parts)
                        if proxima:
                            time_str += f' (next: {proxima})'
                        if time_str.strip():
                            lines.append(f'- {time_str.strip()}')

        # URL
        url_slug = event.get('url', '')
        if url_slug:
            lines.append(f'**URL:** https://www.alternativateatral.com/{url_slug}')

        # Tickets
        url_entradas = event.get('url_entradas', '')
        if url_entradas:
            lines.append(f'**Tickets:** {url_entradas}')

        lines.append('')  # Blank line between events

    return '\n'.join(lines)


async def crawl_json_api(website, cursor, connection, crawl_run_id):
    """Crawl a website via HTTP GET to a JSON/JSONP API endpoint.

    Args:
        website: Website dict with json_api_config, name, id, etc.
        cursor: Database cursor
        connection: Database connection
        crawl_run_id: ID of the current crawl run

    Returns:
        crawl_result_id if successful, None otherwise
    """
    name = website['name']
    config = website.get('json_api_config', {})

    if not config:
        print(f"  Skipping {name}: no json_api_config")
        return None

    # Create safe filename and crawl result record
    safe_filename = create_safe_filename(name, '.md')
    crawl_result_id = db.create_crawl_result(
        cursor, connection, crawl_run_id, website['id'], safe_filename
    )

    try:
        # Determine URL
        url = config.get('base_url')
        if not url:
            urls = website.get('urls', [])
            if urls:
                url = urls[0]['url'] if isinstance(urls[0], dict) else urls[0]
        if not url:
            db.update_crawl_result_failed(cursor, connection, crawl_result_id, "No URL configured")
            db.update_website_last_crawled(cursor, connection, website['id'])
            return None

        print(f"  Crawling {name} via JSON API...")
        print(f"    - GET {url}")

        # HTTP GET
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()

        raw_text = response.text

        # Strip JSONP wrapper if configured
        jsonp_callback = config.get('jsonp_callback')
        if jsonp_callback:
            raw_text = strip_jsonp(raw_text, jsonp_callback)

        # Parse JSON
        data = json.loads(raw_text)

        # Navigate data_path (e.g., 'espectaculos')
        data_path = config.get('data_path', '')
        if data_path:
            for key in data_path.split('.'):
                if key and isinstance(data, dict):
                    data = data.get(key, {})

        total_events = len(data) if isinstance(data, dict) else 0
        print(f"    - Total events in API: {total_events}")

        # Filter by date window
        date_window_days = config.get('date_window_days', 30)
        if isinstance(data, dict):
            filtered = filter_by_date_window(data, date_window_days)
        else:
            filtered = data

        filtered_count = len(filtered) if isinstance(filtered, dict) else 0
        print(f"    - Events after date filter ({date_window_days}d): {filtered_count}")

        # Flatten to markdown
        fields_include = config.get('fields_include')
        markdown = flatten_events_to_markdown(filtered, fields_include)

        if not markdown.strip():
            db.update_crawl_result_failed(
                cursor, connection, crawl_result_id, "No events after filtering"
            )
            db.update_website_last_crawled(cursor, connection, website['id'])
            return None

        # Store markdown (same as browser crawl path)
        db.update_crawl_result_crawled(cursor, connection, crawl_result_id, markdown)
        db.update_website_last_crawled(cursor, connection, website['id'])

        print(f"    - Stored {len(markdown)} chars of markdown ({filtered_count} events)")
        return crawl_result_id

    except Exception as e:
        error_msg = str(e)
        print(f"    - Error crawling {name}: {error_msg}")
        db.update_crawl_result_failed(cursor, connection, crawl_result_id, error_msg)
        db.update_website_last_crawled(cursor, connection, website['id'])
        return None


def resolve_url_templates(url):
    """Resolve date template placeholders in URLs.

    Supported placeholders:
        {{month}}           - current month name, lowercase (e.g. "february")
        {{year}}            - current year (e.g. "2026")
        {{next_month}}      - next month name, lowercase
        {{next_month_year}} - year of the next month (handles Dec→Jan rollover)
    """
    if '{{' not in url:
        return url
    now = datetime.now()
    next_month_date = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
    replacements = {
        '{{month}}': now.strftime('%B').lower(),
        '{{year}}': str(now.year),
        '{{next_month}}': next_month_date.strftime('%B').lower(),
        '{{next_month_year}}': str(next_month_date.year),
    }
    for placeholder, value in replacements.items():
        url = url.replace(placeholder, value)
    return url


def create_safe_filename(name, extension=None):
    """Generate a safe filesystem name from a string."""
    safe = "".join(c for c in name if c.isalnum() or c in (' ', '_')).rstrip()
    safe = safe.replace(' ', '_').lower()
    if extension:
        safe += extension
    return safe


async def crawl_website(crawler, website, cursor, connection, crawl_run_id):
    """
    Crawl a website and store the content in the database.

    Args:
        crawler: AsyncWebCrawler instance
        website: Website dict with urls, name, selector, etc.
        cursor: Database cursor
        connection: Database connection
        crawl_run_id: ID of the current crawl run

    Returns:
        crawl_result_id if successful, None otherwise
    """
    name = website['name']
    urls = website['urls']

    if not urls:
        print(f"  Skipping {name}: no URLs configured")
        return None

    # Create safe filename from website name
    safe_filename = create_safe_filename(name, '.md')

    # Create crawl result record
    crawl_result_id = db.create_crawl_result(
        cursor, connection, crawl_run_id, website['id'], safe_filename
    )

    try:
        # Generate JavaScript code for dynamic content loading
        # Use custom js_code from database if set, otherwise generate from selector/num_clicks
        js_code = website.get('js_code') or ""
        if not js_code:
            selector = website.get('selector')
            num_clicks = website.get('num_clicks', 2)
            if selector and num_clicks:
                js_code = f"for (let i = 0; i < {num_clicks}; i++) {{await new Promise(resolve => setTimeout(resolve, 1000)); document.querySelector('{selector}').click();}}"

        # Configure deep crawling strategy based on keywords
        keywords = website.get('keywords')
        if keywords:
            filters = [f"*{k.strip()}*" for k in keywords.split(', ')]
            max_pages = website.get('max_pages', 30)
            url_filter = URLPatternFilter(patterns=filters)
            deep_crawl_strategy = BestFirstCrawlingStrategy(
                max_depth=1,
                include_external=True,
                filter_chain=FilterChain([url_filter]),
                max_pages=max_pages
            )
        else:
            deep_crawl_strategy = BestFirstCrawlingStrategy(max_depth=0)

        # Get per-website crawl settings (with defaults)
        delay_seconds = website.get('delay_before_return_html') or 5
        filter_threshold = website.get('content_filter_threshold')
        scan_full_page = website.get('scan_full_page', True)
        remove_overlays = website.get('remove_overlay_elements', False)
        scroll_delay = website.get('scroll_delay') or 0.2
        crawl_timeout = website.get('crawl_timeout') or DEFAULT_CRAWL_TIMEOUT

        # Configure markdown generator with optional content filter
        # If filter_threshold is explicitly 0 or None, disable the filter entirely
        if filter_threshold is not None and float(filter_threshold) > 0:
            md_generator = DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(
                    threshold=float(filter_threshold), threshold_type="fixed", min_word_threshold=0
                ),
                options={"ignore_links": False},
            )
        else:
            # No content filter - use raw markdown
            md_generator = DefaultMarkdownGenerator(
                options={"ignore_links": False},
            )

        # Configure crawler
        # Note: Don't exclude 'form' as some sites wrap content in forms (e.g., Park Slope Parents calendar)
        # Note: Don't exclude 'header' as some sites use <header> inside articles for event titles (e.g., Prospect Park)
        crawler_config = CrawlerRunConfig(
            word_count_threshold=5,
            excluded_tags=[],
            process_iframes=True,
            cache_mode=CacheMode.BYPASS,  # Don't use cache for fresh content
            js_code=js_code,
            remove_overlay_elements=remove_overlays,
            delay_before_return_html=delay_seconds,
            scan_full_page=scan_full_page,
            scroll_delay=scroll_delay,
            page_timeout=60000,
            wait_until='domcontentloaded',  # Use domcontentloaded instead of networkidle for faster/more reliable JS navigation
            ignore_body_visibility=True,  # Don't skip invisible body elements
            deep_crawl_strategy=deep_crawl_strategy,
            markdown_generator=md_generator,
        )

        print(f"  Crawling {name} (timeout: {crawl_timeout}s)...")
        combined_markdown = ""

        async def crawl_urls():
            """Inner function to crawl all URLs, can be wrapped with timeout."""
            nonlocal combined_markdown
            for url_data in urls:
                # Handle both dict format (with js_code) and string format (legacy)
                if isinstance(url_data, dict):
                    url = resolve_url_templates(url_data['url'])
                    url_js_code = url_data.get('js_code')
                else:
                    url = resolve_url_templates(url_data)
                    url_js_code = None

                # Use per-URL js_code if set, otherwise use website-level config
                if url_js_code:
                    url_config = CrawlerRunConfig(
                        word_count_threshold=5,
                        excluded_tags=[],
                        process_iframes=True,
                        cache_mode=CacheMode.BYPASS,
                        js_code=url_js_code,
                        remove_overlay_elements=remove_overlays,
                        delay_before_return_html=delay_seconds,
                        scan_full_page=scan_full_page,
                        scroll_delay=scroll_delay,
                        page_timeout=60000,
                        wait_until='domcontentloaded',
                        ignore_body_visibility=True,
                        deep_crawl_strategy=deep_crawl_strategy,
                        markdown_generator=md_generator,
                    )
                else:
                    url_config = crawler_config

                print(f"    - Processing {url}")
                url_content = ""
                page_count = 0

                for result in await crawler.arun(url=url, config=url_config):
                    page_count += 1
                    # Debug: show what we received
                    html_len = len(result.html) if result and result.html else 0
                    has_error = bool(result.error_message) if result else False
                    print(f"      Page {page_count}: html={html_len}, success={result.success if result else False}, error={result.error_message if has_error else 'none'}")

                    # Debug: warn if HTML has no body (crawl4ai bug on some sites)
                    if result and result.html and html_len > 1000:
                        raw_len = len(result.markdown.raw_markdown) if result.markdown and result.markdown.raw_markdown else 0
                        has_body = '<body' in result.html.lower()
                        if not has_body:
                            print(f"      WARNING: HTML missing body tag (html={html_len}, raw_md={raw_len}) - possible crawl4ai bug")

                    if result and result.markdown:
                        # Use fit_markdown if available, otherwise fall back to raw_markdown
                        fit_len = len(result.markdown.fit_markdown) if result.markdown.fit_markdown else 0
                        raw_len = len(result.markdown.raw_markdown) if result.markdown.raw_markdown else 0
                        content = result.markdown.fit_markdown
                        if not content or len(content) < 500:
                            # fit_markdown too small, use raw_markdown
                            content = result.markdown.raw_markdown
                        if content:
                            url_content += content + "\n\n"
                        print(f"      Page {page_count}: fit={fit_len}, raw={raw_len}, using={len(content) if content else 0}")

                print(f"    - Crawled {page_count} page(s), {len(url_content)} chars total")
                if url_content:
                    combined_markdown += url + "\n" + url_content

        # Execute crawl with timeout
        try:
            await asyncio.wait_for(crawl_urls(), timeout=crawl_timeout)
        except asyncio.TimeoutError:
            error_msg = f"Crawl timed out after {crawl_timeout} seconds"
            print(f"    - {error_msg}")
            # If we got partial content, still save it
            if combined_markdown.strip():
                print(f"    - Saving partial content ({len(combined_markdown)} chars)")
                db.update_crawl_result_crawled(cursor, connection, crawl_result_id, combined_markdown)
                db.update_website_last_crawled(cursor, connection, website['id'])
                return crawl_result_id
            # No content at all
            db.update_crawl_result_failed(cursor, connection, crawl_result_id, error_msg)
            db.update_website_last_crawled(cursor, connection, website['id'])
            return None

        if not combined_markdown.strip():
            db.update_crawl_result_failed(
                cursor, connection, crawl_result_id, "No content retrieved"
            )
            # Still update last_crawled_at to prevent immediate retry
            db.update_website_last_crawled(cursor, connection, website['id'])
            return None

        # Check for minimum content size to catch failed crawls early
        # (e.g., JS-rendered pages that only returned the URL)
        content_size = len(combined_markdown)
        if content_size < MIN_CRAWL_CONTENT_SIZE:
            error_msg = f"Crawled content too small ({content_size} bytes < {MIN_CRAWL_CONTENT_SIZE} minimum) - likely failed to load page content"
            print(f"    - {error_msg}")
            db.update_crawl_result_failed(cursor, connection, crawl_result_id, error_msg)
            db.update_website_last_crawled(cursor, connection, website['id'])
            return None

        # Store crawled content in database
        db.update_crawl_result_crawled(cursor, connection, crawl_result_id, combined_markdown)
        db.update_website_last_crawled(cursor, connection, website['id'])

        print(f"    - Stored {len(combined_markdown)} characters of content")
        return crawl_result_id

    except Exception as e:
        error_msg = str(e)
        print(f"    - Error crawling {name}: {error_msg}")
        db.update_crawl_result_failed(cursor, connection, crawl_result_id, error_msg)
        # Still update last_crawled_at to prevent immediate retry
        db.update_website_last_crawled(cursor, connection, website['id'])
        return None


def get_browser_config(javascript_enabled=True, text_mode=True, light_mode=True, use_stealth=False):
    """
    Get the browser configuration for crawling.

    Args:
        javascript_enabled: Whether to enable JavaScript execution (default: True).
                           Set to False for sites that freeze during JS execution.
        text_mode: If True, disables images for faster text-only crawls (default: True).
        light_mode: If True, uses minimal browser features for speed (default: True).
        use_stealth: If True, uses undetected browser mode to bypass bot detection (default: False).
                    Required for sites like Resident Advisor that have verification pages.

    Note: These are browser-level settings. All websites crawled with this
          config will share the same settings.
    """
    if use_stealth:
        # Use undetected browser mode with stealth features for bot detection bypass
        return BrowserConfig(
            headless=False,
            java_script_enabled=javascript_enabled,
            text_mode=text_mode,
            light_mode=light_mode,
            use_managed_browser=True,
            enable_stealth=True,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            extra_args=['--disable-blink-features=AutomationControlled']
        )
    else:
        # Standard browser mode
        return BrowserConfig(
            headless=False,
            java_script_enabled=javascript_enabled,
            text_mode=text_mode,
            light_mode=light_mode
        )
