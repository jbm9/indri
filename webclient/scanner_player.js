function ScannerPlayer() {
    var tg_follow = [ 0x3270, 0x3290 ];

    var backlog = []; // enqueued-but-unavailable files
    var queue = []; // actual playlist

    var talkgroups = null;

    var playing = false;
    var playing_entry;

    var play_anything = false; // fill dead space
    this.setPlayAnything = function(v) { play_anything = v; }

    var printQueueDebug = false; // incredibly noisy, but also super handy sometimes
    this.setPrintQueueDebug = function(v) { printQueueDebug = v; }

    var sysac = audioContext = window.AudioContext || window.webkitAudioContext;
    var context = new sysac();
    var source = context.createBufferSource();

    // kludge to allow this to work in ios
    function ios_unlock_sound(event) {
	var buffer = context.createBuffer(1, 1, 22050);    
	source = context.createBufferSource();
	source.buffer = buffer;    
	source.connect(context.destination);    
	source.noteOn(0);    
	window.removeEventListener("touchend", ios_unlock_sound, false);
    }

    window.addEventListener("touchend", ios_unlock_sound, false);


    var uidiv = null; // <div> for our UI

    var base_url = "http://localhost/"; // base of all WAV urls

    var paused = false;

    this.configUpdate = function(config) {
	base_url = config["wav_base_uri"];
    }

    this.setBaseURL = function(u) { base_url = u; }


    this.registerTalkgroups = function(tgs) { 
	talkgroups = tgs;
    };

    var pause_unpause = function(cb) {
	if (!paused) {
	    context.suspend().then(function() {
		paused = true;
		if (cb) cb(paused);
	    });

	} else {
	    context.resume().then(function() {
		paused = false;
		if (cb) cb(paused);
	    });
	}
    };
    this.pauseUnpause = pause_unpause;

    var notifyActiveWavTG = function(s) {
	// Let's check if the browser supports notifications
	if (!("Notification" in window)) {
	    console.log("Notifications not supported.")
	    return;
	}

	// Let's check whether notification permissions have already been granted
	if (Notification.permission === "granted") {
	    // If it's okay let's create a notification
	    var notification = new Notification(s);
	    setTimeout(notification.close.bind(notification), 5000);
	}

	// Otherwise, we need to ask the user for permission
	else if (Notification.permission !== 'denied') {
	    Notification.requestPermission(function (permission) {
		// If the user accepts, let's create a notification
		if (permission === "granted") {
		    var notification = new Notification(s);
		    setTimeout(notification.close.bind(notification), 5000);
		}
	    });
	}
    }


    var play = function(entry) {
	var url = base_url + entry.filename;

	set_current_tg("(loading) " + entry.tg, entry.avg_power);

	if (printQueueDebug) console.debug("play: " + url);
	playing = true;
	playing_entry = entry;

	var request = new XMLHttpRequest();

	request.open("GET", url, true);
	request.responseType = "arraybuffer";

	request.onload = function() {
	    if (request.status != 200) {
		console.error("Error fetching wav: status=" + request.status);
		play_next();
		return;
	    }

	    var bytes = request.response;

            context.decodeAudioData(bytes, function(buffer) {
		try {
		    source.stop(); // just in case
		} catch(e) { }
		source = context.createBufferSource();
		source.onended = play_next;
		source.buffer = buffer;

		source.connect(context.destination);
		source.start(0);
		set_current_tg(entry.tg, entry.avg_power);
            },
				    function(e) { console.error("Audio decode error: " + e); play_next(); }
				   );
	};
	request.send();
    };


    var play_next = function() {
	try {
	    if (playing) source.stop();
	} catch(e) {
	}

	if (play_anything && 0 == queue.length && 0 != backlog.length) {
	    var filename = null
	    var entry;

	    for (var i = backlog.length-1; i >= 0; i--) { // LIFO
		entry = backlog[i];
		if (entry.available) {
		    filename = entry.path;
		    break;
		}
		entry = null; // sentinel value
	    }

	    if (filename) {
		var newbacklog = backlog.filter(function(e,i,a) { return e.filename != filename; });
		backlog = newbacklog;

		if (null == entry.tg) entry.tg = 0
		queue.push(entry);
	    }
	}

	if (queue.length) {
	    play(queue.shift());
	} else {
	    playing = false;
	    set_current_tg(null);
	}
    }

    
    var flushbacklog = function() {
	var avails = backlog.filter(function(e,i,a) { return e.available && e.interesting; });

	var tCutoff = new Date() - 20000;
	var newbacklog = backlog.filter(function(e,i,a) { return !(e.available && e.interesting) && e.added > tCutoff; });
	backlog = newbacklog;

	for (var i = 0; i < avails.length; i++) queue.push(avails[i]);
	if (avails.length && !playing) play_next();

	if (play_anything && !playing) play_next();
    }

    var available = function(filename) {

	var got_hit = false;

	for (var i = 0; i < backlog.length; i++) {
	    if (filename == backlog[i].filename) {
		backlog[i].available = true;
		got_hit = true;
		if (printQueueDebug) console.debug("Got hit: " + filename);
	    }
	}
	if (!got_hit) {
	    if (printQueueDebug) console.debug("available (" + backlog.length + "): " + filename);
	    backlog.push({"filename": filename, 
			  "tg": null, 
			  "available": true, 
			  "added": new Date(), 
			  "interesting": false,
			  "avg_power": -101.0});
	}

	//	  window.setTimeout(flushbacklog, 1000);
	flushbacklog();
    }
    this.available = available;


    this.handle_tgfile = function(response) {
	var tg = response.tg
	var avg_power = response.avg_power;
	var filename = response.path;

	var interesting = talkgroups.following(tg);

	if (playing && filename == playing_entry.filename) {
	    set_current_tg(tg, avg_power);
	}


	var got_hit = false;


	for (var i = 0; i < backlog.length; i++) {

	    if (filename == backlog[i].filename) {
		backlog[i].tg = tg;
		backlog[i].available = true;
		backlog[i].avg_power = avg_power;
		got_hit = true;
		if (printQueueDebug) console.debug("qualified filename: " + filename);
	    }
	}
	if (!got_hit) {
	    if (printQueueDebug) console.debug("Unqualified filename: " + filename + " tg: " + tg);
	    backlog.push({"filename": filename, 
			  "tg": tg, 
			  "available": false, 
			  "added": new Date(), 
			  "interesting": interesting,
			  "avg_power": avg_power});
	}

	//	  window.setTimeout(flushbacklog, 1000);
	flushbacklog();
    }

    this.handle_fileup = function(response) {
	available(response.path);
    }

    var set_current_tg = function(s, pwr) {
	var curtg = uidiv.find(".current_tg");
	if (null == s) {
	    curtg.text("-idle-");
	    curtg.css("background-color", "#ccc")
	} else {
	    var tgId = parseInt(s);
	    var decode = "TG-" + tgId.toString(16);
	    if (talkgroups) {
		var tg = talkgroups.lookup(tgId);
		if (pwr) 
		    decode = "[" + (parseInt(pwr*10)/10.0) + "] " + decode
		if (tg)
		    decode += "--" + tg.category + "/" + tg.short + 
		              "(" + tg.long + ")";
	    }

	    curtg.text(decode);
	    if (tgId)
		notifyActiveWavTG(decode);
	    curtg.css("background-color", "#ecc")
	}
    }



    var setup_ui = function() {
	if (!uidiv) return;

	var tgdisplay = document.createElement("div");
	var newlabel = document.createElement("span");
	newlabel.textContent = "Now playing:";
	tgdisplay.appendChild(newlabel);

	var curtg = document.createElement("span");
	curtg.classList.add("current_tg");
	tgdisplay.appendChild(curtg);

	uidiv.append(tgdisplay);


	set_current_tg(null);
    }


    this.initUI = function(uidiv_in) {
	uidiv = uidiv_in;

	var pause_button = uidiv.find("#playpause");
	pause_button.click(function() {
	    pause_unpause(function(paused) {
		pause_button.text(paused ? "|>" : "||");
	    });
	});


	var next_button = uidiv.find("#playnext");
	next_button.click(function() {
	    play_next();
	});


	var any_button = uidiv.find("#playany");
	any_button.click(function() {
	    play_anything = !play_anything;
	    any_button.text(play_anything ? "*" : "_");
	});
    }

    return this;
};
