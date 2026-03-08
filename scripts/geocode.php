#!/usr/bin/env php
<?php
/**
 * Geocode venue names or addresses using Google Maps Geocoding API
 * Results are biased toward Buenos Aires, Argentina by default.
 *
 * Usage:
 *   php scripts/geocode.php "MALBA"
 *   php scripts/geocode.php "Teatro Colon"
 *   php scripts/geocode.php --json "Centro Cultural Kirchner"
 *   php scripts/geocode.php --batch venues.txt
 *
 * Environment:
 *   GOOGLE_MAPS_API_KEY - Required. Set in .env or export directly.
 */

// Load .env file if it exists
$env_file = __DIR__ . '/../.env';
if (file_exists($env_file)) {
    $lines = file($env_file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        if (strpos($line, '#') === 0) continue;
        if (strpos($line, '=') !== false) {
            list($key, $value) = explode('=', $line, 2);
            $key = trim($key);
            $value = trim($value, " \t\n\r\0\x0B\"'");
            if (!getenv($key)) {
                putenv("$key=$value");
            }
        }
    }
}

// Parse command line arguments
$show_help = in_array('--help', $argv) || in_array('-h', $argv);
$json_output = in_array('--json', $argv) || in_array('-j', $argv);
$batch_mode = in_array('--batch', $argv) || in_array('-b', $argv);

if ($show_help) {
    echo <<<HELP
Geocode venue names or addresses using Google Maps Geocoding API
Results are biased toward Buenos Aires, Argentina by default.

Usage:
  php scripts/geocode.php [options] <venue name or address>
  php scripts/geocode.php --batch <file>

Options:
  --json, -j      Output as JSON (for programmatic use)
  --batch, -b     Read venues from file (one per line)
  --help, -h      Show this help message

Environment:
  GOOGLE_MAPS_API_KEY    Required. Your Google Maps API key.
                         Can be set in .env file or exported.

Examples:
  php scripts/geocode.php "MALBA"
  php scripts/geocode.php "Teatro Colon"
  php scripts/geocode.php --json "Centro Cultural Kirchner"
  php scripts/geocode.php --batch venues.txt

Output (default):
  Name: MALBA
  Address: Av. Pres. Figueroa Alcorta 3415, C1425 CABA, Argentina
  Lat: -34.57740
  Lng: -58.40390

Output (--json):
  {"name":"MALBA","address":"Av. Pres. Figueroa Alcorta 3415, C1425 CABA, Argentina","lat":-34.5774,"lng":-58.4039}

Note: The script automatically biases results toward Buenos Aires.
      Just provide a venue name - no need to add "Buenos Aires" or addresses.

HELP;
    exit(0);
}

// Get API key
$api_key = getenv('GOOGLE_MAPS_API_KEY');
if (!$api_key) {
    fwrite(STDERR, "Error: GOOGLE_MAPS_API_KEY environment variable is required.\n");
    fwrite(STDERR, "Set it in .env file or export GOOGLE_MAPS_API_KEY=your_key\n");
    exit(1);
}

// Buenos Aires bounding box (SW corner to NE corner)
// Covers Ciudad Autonoma de Buenos Aires (CABA)
define('BA_BOUNDS', '-34.75,-58.60|-34.50,-58.28');

/**
 * Geocode a venue name or address, biased toward Buenos Aires
 */
function geocode_address($query, $api_key) {
    $url = 'https://maps.googleapis.com/maps/api/geocode/json?' . http_build_query([
        'address' => $query,
        'bounds' => BA_BOUNDS,         // Bias results toward Buenos Aires
        'region' => 'ar',              // Prefer Argentine results
        'components' => 'country:AR',  // Restrict to Argentina
        'key' => $api_key,
    ]);

    $context = stream_context_create([
        'http' => [
            'timeout' => 10,
            'ignore_errors' => true,
        ],
    ]);

    $response = @file_get_contents($url, false, $context);
    if ($response === false) {
        return ['error' => 'Failed to connect to Google Maps API'];
    }

    $data = json_decode($response, true);
    if (!$data) {
        return ['error' => 'Invalid JSON response from API'];
    }

    if ($data['status'] === 'ZERO_RESULTS') {
        return ['error' => 'No results found for address'];
    }

    if ($data['status'] === 'REQUEST_DENIED') {
        return ['error' => 'API request denied: ' . ($data['error_message'] ?? 'Unknown error')];
    }

    if ($data['status'] === 'OVER_QUERY_LIMIT') {
        return ['error' => 'API query limit exceeded'];
    }

    if ($data['status'] !== 'OK' || empty($data['results'])) {
        return ['error' => 'API error: ' . ($data['status'] ?? 'Unknown')];
    }

    $result = $data['results'][0];
    $location = $result['geometry']['location'];

    // Extract a short name from address components
    $name = null;
    $street_number = null;
    $route = null;
    foreach ($result['address_components'] as $component) {
        if (in_array('street_number', $component['types'])) {
            $street_number = $component['short_name'];
        }
        if (in_array('route', $component['types'])) {
            $route = $component['short_name'];
        }
        if (in_array('establishment', $component['types']) || in_array('point_of_interest', $component['types'])) {
            $name = $component['long_name'];
        }
    }

    // Build name from street address if no establishment name
    if (!$name && $street_number && $route) {
        $name = "$street_number $route";
    } elseif (!$name) {
        $name = $result['formatted_address'];
    }

    return [
        'name' => $name,
        'address' => $result['formatted_address'],
        'lat' => $location['lat'],
        'lng' => $location['lng'],
        'place_id' => $result['place_id'] ?? null,
        'types' => $result['types'] ?? [],
    ];
}

/**
 * Format result for display
 */
function format_result($result, $json_output = false) {
    if (isset($result['error'])) {
        if ($json_output) {
            return json_encode(['error' => $result['error']]);
        }
        return "Error: {$result['error']}";
    }

    if ($json_output) {
        return json_encode([
            'name' => $result['name'],
            'address' => $result['address'],
            'lat' => $result['lat'],
            'lng' => $result['lng'],
        ]);
    }

    return sprintf(
        "Name: %s\nAddress: %s\nLat: %.5f\nLng: %.5f",
        $result['name'],
        $result['address'],
        $result['lat'],
        $result['lng']
    );
}

// Get addresses to geocode
$addresses = [];

// Filter out option flags from argv
$args = array_filter($argv, function($arg) {
    return strpos($arg, '-') !== 0 && $arg !== $GLOBALS['argv'][0];
});
$args = array_values($args);

if ($batch_mode) {
    // Find the file argument after --batch
    $batch_index = array_search('--batch', $argv) ?: array_search('-b', $argv);
    $file = $argv[$batch_index + 1] ?? null;

    if (!$file || !file_exists($file)) {
        fwrite(STDERR, "Error: Batch file not found: $file\n");
        exit(1);
    }

    $addresses = array_filter(array_map('trim', file($file)));
} elseif (!empty($args)) {
    $addresses = [implode(' ', $args)];
} else {
    fwrite(STDERR, "Error: No address provided.\n");
    fwrite(STDERR, "Usage: php scripts/geocode.php \"address\"\n");
    fwrite(STDERR, "       php scripts/geocode.php --help\n");
    exit(1);
}

// Process addresses
$results = [];
foreach ($addresses as $address) {
    $result = geocode_address($address, $api_key);
    $results[] = $result;

    if (!$batch_mode || !$json_output) {
        echo format_result($result, $json_output) . "\n";
        if ($batch_mode && count($addresses) > 1) {
            echo "---\n";
        }
    }
}

// For batch mode with JSON, output all results at once
if ($batch_mode && $json_output) {
    echo json_encode($results, JSON_PRETTY_PRINT) . "\n";
}

exit(0);
