function ScannerConnection() {
    var disabled = false;
    this.disabled = disabled;

    // our actual websocket connection
    var connection = null;

    // state: disconnected/connecting/timeout/connected (no scanner)/live (with scanner)
    var connection_state = "disconnected";

    // Print messages of this type (array of 'type' values, or just true)
    var print_messages = false;
    this.setPrintMessages = function(v) { print_messages = v; };

    var ui = new ScannerTemplate($("#connstatus"), $("#tmpl-connection-status"));


    //////////////////////////////////////////////////////////////
    //
    // Monitor health of connection to the scanner hardware
    //

    // last 'ping' packet from the scanner
    var lastping = 0;
    var lastping_ts = 0;

    var SCANNER_TIMEOUT = 5;  // 2.5 'ping' packet periods

    function handlePing(response) {
	lastping_ts = response.ts
	lastping = new Date();
    }

    function scannerTimeoutTriggered(timeout_s) {
	if (!connection) return null; // this is kinda nonsense

	var tnow = new Date();
	var dt = tnow - lastping;
	return (dt > timeout_s*1000);
    }
    this.scannerTimeoutTriggered = scannerTimeoutTriggered;



    //////////////////////////////////////////////////////////////
    //
    // Monitor health of connection to the websocket
    //

    // last packet of any type from the websocket
    var lastpkt = 0;

    var WEBSOCKET_TIMEOUT = 5; // 2.5 'ka' packet periods

    function handleKA(response) {}; // do nothing
    function websocketTimeoutTriggered(timeout_s) {
	if (!connection) return null;

	var tnow = new Date();
	var dt = tnow - lastpkt;
	return (dt > timeout_s*1000);
    }

    ////////////////////////////////////////////////////


    // TODO: refactor control counts out into smartnet-specific class
    // Control channel counts (from the smartnet setup)
    var control_counts = { "good": 0,
			   "bad": 0,
			   "exp": 1.0,
			   "offset": 0,
                           "squelch": 0 };



    // Monitor for quality of the smartnet control stream
    function handleControlCounts(response) {
	control_counts.good = response.good;
	control_counts.bad = response.bad;
	control_counts.exp = response.exp;
	control_counts.offset = response.offset;
        control_counts.squelch = response.squelch;
    }


    ////////////////////////////////////////

    // On connection, we get a connected ACK with a system state rundown
    var handleConnected = function(response) {
	console.log("connected!");
	connection_state = "connected";

	var dump = response.states;
	for (var i = 0; i < dump.length; i++) {
	    var cs = dump[i];

	    if (cs.state == "open") {
		handle_response({"type": "start", "freq": cs.freq});
		if (cs.tg != 0) handle_response({"type": "tune", "freq": cs.freq, "tg": cs.tg});
	    } else if(cs.state == "closed") {
		handle_response({"type": "stop", "freq": cs.freq});
	    }
	}

    };

    // All packet handlers get registered in this
    // NB: special handler '_CLOSE_' for socket close events
    var handlers = { "ping": handlePing,
		     "control_counts": handleControlCounts,
		     "connected": handleConnected,
		     "ka": handleKA}; 

    // Register a new packet handler from outside
    this.register = function(evtname, handler) {
	handlers[evtname] = handler;
    }

    // Mulitplexer for incoming packets
    var handle_response = function(response, e) {
	if (false === print_messages) {
	} else if (true === print_messages) {
	    console.debug(response);
	} else if (-1 != print_messages.indexOf(response.type)) {
	    console.debug(response);
	}

	lastpkt = new Date();

	var msgtype = response.type;
	if (!msgtype) {
	    console.log("Error: message without type: " + e);
	    return;
	}


	var handler = handlers[msgtype];
	if (!handler) {
	    console.log("Error: unhandled message type: " + msgtype + ": " + e);
	    return;
	}

	handler(response);
    };


    // Establish our connection
    this.reconnect = function(hostname) {
	if (connection) return false;
	if (disabled) return true;

	connection_state = "connecting";
	connection = new WebSocket("ws://" + hostname + ":8081");

	connection.onopen = function() {
	    console.log("Websocket connected: " + hostname);
	    lastping = new Date(); // give it a freebie
	    lastpkt = new Date();
	}; // nothing for now

	connection.onerror = function(error) {
	    console.log("Websocket error: " + error);
	};

	connection.onclose = function(e) {
	    console.log("Closed: " + e);
	    connection = null;
	    var handler = handlers["_CLOSE_"];
	    if (handler)
		handler();
	};

	connection.onmessage = function(e) {
	    var response = JSON.parse(e.data);
	    handle_response(response, e);
	}
	return true;
    };

    this.disconnect = function(disable) {
	disabled = disable;
	connection.close();
    };


    var check_timeouts = function() {
	if (!connection) {
	    return;
	}

	var scanner_to = scannerTimeoutTriggered(SCANNER_TIMEOUT);
	var websocket_to = websocketTimeoutTriggered(WEBSOCKET_TIMEOUT);

	if (!websocket_to && !scanner_to) {
	    connection_state = "live";
	} else if (!websocket_to && scanner_to) {
	    console.log("Websocket okay, but scanner is timed out: " + new Date());
	    console.log("Last scanner ping: " + lastping);
	    connection_state = "connected";
	} else if (websocket_to) {
	    connection_state = "timeout";
	    console.log("Connection timeout: " + new Date());
	    connection_state = "disconnected";
	    connection.close();
	}
    }

    var template_data = function() {
	var data = {};

	data["websocket_connected"] = "C";
	data["websocket_connected_class"] = "websocket_connected_-_" + connection_state;


	data["freq_offset"] = parseInt(control_counts["offset"]);
	if (data["freq_offset"] > 0) data["freq_offset"] = "+" + data["freq_offset"];


	var pkts_seen = control_counts["good"] + control_counts["bad"];
	var dt = control_counts["dt"];
	var pkts_expected = control_counts["exp"];

	var decode_perc = parseInt(100 * pkts_seen/pkts_expected)/100.0;

	data["decode_stats"] = decode_perc; // Super handy but probably misleading as "xx%"

	var decode_bucket = "";
	if        (decode_perc >  95) {  decode_bucket =  "ok";
	} else if (decode_perc >= 90) {  decode_bucket =  "90";
	} else if (decode_perc >= 80) {  decode_bucket =  "80";
	} else if (decode_perc >= 70) {  decode_bucket =  "70";
	} else                        {  decode_bucket = "bad";  }

	data["decode_stats_class"] = "decode_stats_-_" + decode_bucket;

        data["squelch"] = parseInt(100*control_counts["squelch"])/100.0;
        return data;
    };


    // Actually update the UI
    this.updateUI = function() {
	check_timeouts(); // side-effect: update connection_state
        ui.update( template_data() );
    };

    return this;
}
