function ScannerConnection() {
    var connection = null;

    var lastping = 0;
    var lastping_ts = 0;


    var lastpkt = 0;

    var uidiv = null;


    function handlePing(response) {
	lastping_ts = response.ts
	lastping = new Date();
    }


    function timeoutTriggered(timeout_s) {
	if (!connection) return null; // this is kinda nonsense

	var tnow = new Date();
	var dt = tnow - lastping;
	return (dt > timeout_s*1000);
    }
    this.timeoutTriggered = timeoutTriggered;

    var handlers = { "ping": handlePing }; // message type => handler(evt)

    this.connect = function(hostname) {
	connection = new WebSocket("ws://" + hostname + ":8081");

	connection.onopen = function() {
	    console.log("Websocket connected");
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
	}

    };

    this.updateUI = function() {
	if (!uidiv) return;
	var live_box = uidiv.find(".connection_live");

	if (!connection || connection.readyState != 1) {
	    live_box.css("background-color", "red")
	    live_box.text(" -- Websocket connection not open ---")
	    return;
	}

	if (timeoutTriggered(5)) {
	    var tnow = new Date();
	    if (tnow - lastpkt > 5) {
		live_box.css("background-color", "red");
	        live_box.text("Long delay:" + lastping);
//		connection.close()
	    } else
		live_box.css("background-color", "yellow");
	} else {
	    live_box.css("background-color", "green");
	    live_box.text(" OK ");
	}
    }

    this.attachUI = function(uidiv_in) {
	uidiv = uidiv_in;

	var live_box = document.createElement("span");
	live_box.classList.add("connection_live");
	live_box.textContent = "***";
	uidiv.append(live_box);
    }

    this.register = function(evtname, handler) {
	handlers[evtname] = handler;
    }

    return this;
}
