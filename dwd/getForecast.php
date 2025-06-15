<?php

/*
 * storeStations.php contains a php array of dwd stations: $storeStations = [ ..., ..., ... ];
*/
$storeStations = true;
if ( file_exists( __DIR__ . '/storeStations.php' ) ) {
    include __DIR__ . '/storeStations.php';
}

if ( isset( $argv[1] ) ) {
	$station = $argv[1];
	$storeStations = [];
	$storeStations[] = $station;
}

/*
$zipfile = 'MOSMIX_S_LATEST_240.kmz';
$url = 'https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_S/all_stations/kml/' . $zipfile;
*/

$availableFields = [
	'PPPP',  'E_PPP',  'TX',    'TTT',   'E_TTT',  'Td',    'E_Td',  'TN',    'TG',    'TM',
	'T5cm',  'DD',     'E_DD',  'FF',    'E_FF',   'FX1',   'FX3',   'FX625', 'FX640', 'FX655',
	'FXh',   'FXh25',  'FXh40', 'FXh55', 'N',      'Neff',  'Nlm',   'Nh',    'Nm',    'Nl',
	'N05',   'VV',     'VV10',  'wwM',   'wwM6',   'wwMh',  'wwMd',  'ww',    'ww3',   'W1W2',
	'wwP',   'wwP6',   'wwPh',  'wwPd',  'wwZ',    'wwZ6',  'wwZh',  'wwD',   'wwD6',  'wwDh',
	'wwC',   'wwC6',   'wwCh',  'wwT',   'wwT6',   'wwTh',  'wwTd',  'wwS',   'wwS6',  'wwSh',
	'wwL',   'wwL6',   'wwLh',  'wwF',   'wwF6',   'wwFh',  'DRR1',  'RR6c',  'RRhc',  'RRdc',
	'RR1c',  'RRS1c',  'RRL1c', 'RR3c',  'RRS3c',  'R101',  'R102',  'R103',  'R105',  'R107',
	'R110',  'R120',   'R130',  'R150',  'RR1o1',  'RR1w1', 'RR1u1', 'R600',  'R602',  'R610',
	'R650',  'Rh00',   'Rh02',  'Rh10',  'Rh50',   'Rd00',  'Rd02',  'Rd10',  'Rd50',  'SunD',
	'RSunD', 'PSd00',  'PSd30', 'PSd60', 'RRad1',  'Rad1h', 'SunD1', 'SunD3', 'PEvap', 'WPc11',
	'WPc31', 'WPc61',  'WPch1', 'WPcd1'
];

function debug( $str ) {
	//echo "$str\n";
}

$cred = explode( "\n", file_get_contents( realpath(dirname(__FILE__)) . '/../db.cred' ) );
$mysqli = new mysqli( $cred[0], $cred[1], $cred[2], $cred[3] );
if ($mysqli->connect_errno) {
    die( "Failed to connect to MySQL: " . $mysqli->connect_error );
}


$zipfile = '/tmp/dwdforecast.tmp.zip';
$urls = [];
/*
$urls[] = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/N8381/kml/MOSMIX_L_2025060709_N8381.kmz";
$urls[] = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/N8381/kml/MOSMIX_L_2025060715_N8381.kmz";
$urls[] = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/N8381/kml/MOSMIX_L_2025060721_N8381.kmz";
$urls[] = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/N8381/kml/MOSMIX_L_2025060803_N8381.kmz";
$urls[] = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/N8381/kml/MOSMIX_L_2025060809_N8381.kmz";
$urls[] = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/N8381/kml/MOSMIX_L_2025060815_N8381.kmz";
$urls[] = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/N8381/kml/MOSMIX_L_2025060821_N8381.kmz";
*/
foreach ( $storeStations as $station ) {
	// updates every 6 hours
	$urls[] = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/$station/kml/MOSMIX_L_LATEST_$station.kmz";
}
// updates every hour
$urls[] = 'https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_S/all_stations/kml/MOSMIX_S_LATEST_240.kmz';

$commitRows = 0;
foreach ( $urls as $url ) {
	$ts = [];
	$rows = [];

	debug( 'fetch zip ' . $url );
	$zip = file_get_contents( $url );
	if ( $zip !== false ) {
		debug( 'store zip' );
		@unlink( $zipfile );
		file_put_contents( $zipfile, $zip );
		$zip = new ZipArchive;
		debug( 'open zip' );
		$res = $zip->open( $zipfile );
		if ( $res === true ) {
			debug( 'extract kml' );
			$xml = $zip->getFromName( $zip->getNameIndex(0) );
			debug( 'parse kml' );
			$mosmix = new SimpleXMLElement($xml);
			debug( 'get data' );
			$timesteps = $mosmix->children('kml', true)->Document->ExtendedData->children('dwd',true)->ProductDefinition->ForecastTimeSteps->TimeStep;
			for ( $i = 0, $len = count( $timesteps ); $i < $len; $i++ ) {
				#debug( trim($timesteps[$i]) . ' : ' . strtotime( trim($timesteps[$i]) ) );
				$_ts = strtotime( trim($timesteps[$i]) );
				$ts[] = $_ts;
				$row = [ 'timestamp' => $_ts ];
				/*
				for ( $j = 0; $j < count( $sqlFields ); $j++ ) {
					$row[$sqlFields[$j]] = NULL;
				}
				*/
				$rows[] = $row;
			}
			$placemarks = $mosmix->children('kml', true)->Document->Placemark;
			$mysqli->begin_transaction();
			for ( $pi = 0, $len = count( $placemarks ); $pi < $len; $pi++ ) {
				$p = $placemarks[$pi];
				$location = trim( $p->name );
				if ( $storeStations === false || ( is_array( $storeStations ) && !in_array( $location, $storeStations) ) ) {
					continue;
				}
				$sqlData = [];
				$forecasts = $p->ExtendedData->children('dwd',true)->Forecast;

				// aggregate existing properties in data first
				$sqlFields = [];
				for ( $fi = 0, $flen = count( $forecasts ); $fi < $flen; $fi++ ) {
					$f = $forecasts[$fi];
					$field = trim( $f['elementName'] );
					if ( in_array( $field, $availableFields ) ) {
						$sqlFields[] = $field;
					}
				}

				$sqlInsert = 'INSERT INTO
					`log`.`weather`
					( `timestamp`, `datetime`, `location`, `' . implode( '`, `', $sqlFields ). '` ) VALUES
					( ?, FROM_UNIXTIME(?), ?, ' . implode(',',array_fill( 0, count($sqlFields), '? ') ) . ')
					ON DUPLICATE KEY UPDATE `' . implode( '` = ?, `', $sqlFields ). '` = ?;';
				$insertStmt = $mysqli->prepare( $sqlInsert );

				//echo "$sqlInsert\n\n";

				/*
				for ( $ri = 0; $ri < count( $rows ); $ri++ ) {
					for ( $j = 0; $j < count( $sqlFields ); $j++ ) {
						$rows[$ri][$sqlFields[$j]] = NULL;
					}
				}
				*/

				for ( $fi = 0, $flen = count( $forecasts ); $fi < $flen; $fi++ ) {
					$f = $forecasts[$fi];
					$field = trim( $f['elementName'] );
					$values = preg_split( '/\s+/', trim($f->value) );
					for ( $vi = 0, $vlen = count( $values ); $vi < $vlen; $vi++ ) {
						//if ( array_key_exists( $field, $rows[$vi] ) ) {
							if ( $values[$vi] !== '-' ) {
								$rows[$vi][$field] = (float)$values[$vi];
							} else {
								$rows[$vi][$field] = NULL;
							}
						//}
					}
				}
				// store in db
				for ( $ri = 0, $rlen = count( $rows ); $ri < $rlen; $ri++ ) {
					$r = $rows[$ri];
					$sqlValues = [ $r['timestamp'] * 1000, $r['timestamp'], $location ];
					// values ...
					for ( $j = 0; $j < count( $sqlFields ); $j++ ) {
						$sqlValues[] = $r[$sqlFields[$j]];
					}
					// on duplicate key ...
					for ( $j = 0; $j < count( $sqlFields ); $j++ ) {
						$sqlValues[] = $r[$sqlFields[$j]];
					}
					#var_dump( $sqlValues );die;
					$insertStmt->bind_param( str_pad( 'iis', 2*count( $sqlFields )+3, 's' ), ...$sqlValues );
					$insertStmt->execute();
					$commitRows++;
					if ( $commitRows % 100 === 99 ) {
						debug ( 'store location forecasts ' . $commitRows );
						$mysqli->commit();
						$mysqli->begin_transaction();
					}
				}
			}
			debug ( 'store location forecasts ' . $commitRows );
			$mysqli->commit();
			//unlink( $file );
		} else {
			// zip broken
			die;
		}
	} else {
		// url broken
		//die;
		continue;
	}
}
