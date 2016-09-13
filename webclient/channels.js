function Channel(entry) {
    var frequency = entry.freq;
    var is_control = entry.is_control;
    var name = entry.name;
    var level = 0;

    var xmitting = false;

    var uidiv = undefined;

    var note = "";

    this.getFrequency = function() { return frequency; }
    this.isControl = function() { return is_control; }
    this.getName = function() { return name; }

    this.isXmit = function() { return xmitting; }


    function updateUI() {
	uidiv.innerHTML = frequency + 
	    "(" + level + ")" + " / " +
	    (xmitting ? "" : "-idle- (") + 
	    note +
	    (xmitting ? "" : ")");
    };


    this.attachUI = function(d) { uidiv = d; updateUI(); }

    this.updateUI = updateUI;

    this.setNote = function(n) { note = n; updateUI(); }
    this.setLevel = function(l) { level = l; updateUI(); }

    clear_xmit_status = function() {
	uidiv.classList.remove("channel_xmit_unknown");
	uidiv.classList.remove("channel_xmit_noxmit");
	uidiv.classList.remove("channel_xmit_inxmit");
    }

    addClass = function(k) { uidiv.classList.add(k); }

    this.startXmit = function() {
	if (is_control) return;
	clear_xmit_status();
	xmitting = true;
	addClass("channel_xmit_inxmit");
	updateUI();
    }

    this.stopXmit = function() {
	if (is_control) return;
	xmitting = false;
	clear_xmit_status();
	addClass("channel_xmit_noxmit");
	updateUI();
    }


    return this;
}


function ChannelBoard() {
    var uidiv = undefined;
    var channels = [];

    var channelIndex = {};

    this.attachUI = function(d) { uidiv = d; };

    this.configUpdate = function(config) {
	channels = [];

	channels = config.channels.map(function(d) { return new Channel(d);});

	channels.forEach(function(c) {
	    channelIndex[c.getFrequency()] = c;
	});

	uidiv.empty();

	channels.forEach(function(c) {
	    var chan_class = "channel_status";
	    if (c.isControl()) chan_class = "channel_status_control";

	    var curdiv = document.createElement("div");

	    curdiv.classList.add(chan_class);
	    if (!c.isControl()) curdiv.classList.add("channel_xmit_unknown");
	    curdiv.id = "channel_status_" + c.getFrequency();

	    c.attachUI(curdiv);

	    uidiv.append(curdiv);
	});
    }


    this.channelStart = function(response) {
	var c = channelIndex[response.freq];
	if (!c) return;

	c.startXmit();
    };

    this.channelStop = function(response) {
	var c = channelIndex[response.freq];
	if (!c) return;

	c.stopXmit();
    };


    this.channelTag = function(response) {
	var c = channelIndex[response.freq];
	if (!c) return;

	var tg = response.tg;
	if (c.isControl()) return;

	c.setNote(tg);
    };

    this.channelLevels = function(response) {
	var levels = response.levels;
	for (var f in levels) {
	    var c = channelIndex[f];
	    if (!c) continue;

	    c.setLevel(levels[f]);
	}
    };

    return this;
}
