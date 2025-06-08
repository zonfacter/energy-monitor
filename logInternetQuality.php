<?php

$cred = explode( "\n", file_get_contents( realpath(dirname(__FILE__)) . '/db.cred' ) );

$mysqli = new mysqli( $cred[0], $cred[1], $cred[2], $cred[3] );
if ($mysqli->connect_errno) {
	die( "Failed to connect to MySQL: " . $mysqli->connect_error );
} else {

	$start = microtime(true);
	$cmd = "ping -i 0.5 -qc 120 -W 15 1.1.1.1";
	$output = [];
	exec( $cmd, $output, $result );

	// Initialize
	$packetsTx = 0;
	$packetsRx = 0;
	$packetsOk = 0;
	$rttMin = NULL;
	$rttAvg = NULL;
	$rttMax = NULL;

	foreach ($output as $line) {
		if (preg_match('/(\d+) packets transmitted, (\d+) received/', $line, $matches)) {
			$packetsTx = (int)$matches[1];
			$packetsRx = (int)$matches[2];
			if ( $packetsTx > 0 ) {
				$packetsOk = $packetsRx / $packetsTx;
			}
		}
		if (preg_match('/rtt min\/avg\/max\/mdev = ([\d.]+)\/([\d.]+)\/([\d.]+)\/[\d.]+ ms/', $line, $matches)) {
			$rttMin = (float)$matches[1];
			$rttAvg = (float)$matches[2];
			$rttMax = (float)$matches[3];
		}
	}


	$end = microtime(true);
	//echo $end - $start . "s\n";
	//echo "$packetsTx $packetsRx\n";
	//echo "$rttMin $rttMax $rttAvg\n";

	$sql = "INSERT INTO `net` ( `packetsTx`, `packetsRx`, `packetsOk`, `rttMin`, `rttMax`, `rttAvg` ) VALUES ( ?, ?, ?, ?, ?, ? );";
	$stmt = $mysqli->prepare($sql);

	if ($stmt === false) {
		die("Prepare failed: " . $mysqli->error);
	}
	
	$stmt->bind_param( "iidddd", $packetsTx, $packetsRx, $packetsOk, $rttMin, $rttMax, $rttAvg );
	
	if (!$stmt->execute()) {
		die("Execute failed: " . $stmt->error);
	}
	
	$stmt->close();

}
