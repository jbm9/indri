function Channel(entry) {
    var frequency = entry.freq;
    var is_control = entry.is_control;
    var name = entry.name;
    var level = -100;
    var xmitting = false;

    var config = null;
    this.configUpdate = function(newconfig) { config = newconfig; }
    var tg = 0;
    this.setTG = function(v) { tg = v; updateUI();}

    this.getTG = function() { return tg; };

    var uidiv = undefined;
    this.getUIDiv = function() { return uidiv; }

    var note = "";

    var talkgroups = null;

    this.getFrequency = function() { return frequency; }
    this.isControl = function() { return is_control; }
    this.getName = function() { return name; }
    
    this.isXmit = function() { return xmitting; }


    var decode_talkgroup = function(tg) {
	if (!talkgroups) return null;
	return talkgroups.lookup(tg);
    }

    var updateUI = function() {
	var disptring = ""

	if (is_control) {
	    if (config)
		xmitting = (level > config.scanner.threshold);
	    dispstring = " -control- ";
	} else if (tg && talkgroups) {
	    var curTG = talkgroups.lookup(tg);
	    if (curTG) {
		dispstring = "TG-" + parseInt(tg).toString(16) + ": " +
		    curTG.category + "/" + curTG.short + ": " +
		    curTG.long;
	    }
	} else {
	    dispstring = name;
	}
	
	$(uidiv).text(frequency + 
	    "(" + level + ")" + " / " +
	    (xmitting ? "" : "-idle- (") + 
		      dispstring +
	    (xmitting ? "" : ")"));

	set_xmit_style();
    };


    this.attachUI = function(d) { uidiv = d; updateUI(); }

    this.updateUI = updateUI;

    this.setNote = function(n) { note = n; updateUI(); }
    this.setLevel = function(l, squelch) { 
	level = l; 
	if (squelch) xmitting = (level > squelch);
	updateUI(); 
    }

    var addClass = function(k) { if(uidiv) uidiv.classList.add(k); }

    var set_xmit_style = function() {
	if (!uidiv) return;
	uidiv.classList.remove("channel_xmit_unknown");
	uidiv.classList.remove("channel_xmit_noxmit");
	uidiv.classList.remove("channel_xmit_inxmit");

	if (xmitting) {
	    addClass("channel_xmit_inxmit");
	} else {
	    addClass("channel_xmit_noxmit");
	}
    }


    this.startXmit = function() {
	xmitting = true;
	updateUI();
    }


    this.stopXmit = function() {
	xmitting = false;
	updateUI();
    }

    this.registerTalkGroups = function(tgs) { talkgroups = tgs; }
	

    return this;
}


function ChannelBoard() {
    var uidiv = undefined;
    var channels = [];

    var channelIndex = {};
    this.channels = channels;
    this.channelIndex = channelIndex;
    var talkgroups = null;

    this.attachUI = function(d) { uidiv = d; };

    this.registerTalkgroups = function(tgs) { 
	talkgroups = tgs; 
	channels.forEach(function(c) { c.registerTalkGroups(tgs) });
    };

    this.configUpdate = function(config) {
	channels.length = 0

	for (var f_i in channelIndex) channelIndex[f_i] = undefined;

	config.channels.forEach(function(d) { channels.push(new Channel(d)) });
	channels.forEach(function(c) {
	    c.registerTalkGroups(talkgroups); 
	    c.configUpdate(config);
	});
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
    };


    this.channelStart = function(response) {
	var c = channelIndex[response.freq];
	if (!c) return;
	if (c.isXmit) return;

	c.startXmit();
	talkgroups.updateUI();
    };

    this.channelStop = function(response) {
	var c = channelIndex[response.freq];
	if (!c) return;
	if (!c.isXmit) return;

	c.stopXmit();
	talkgroups.updateUI();
    };


    this.channelTag = function(response) {
	var c = channelIndex[response.freq];
	if (!c) return;

	var tg = response.tg;
	if (c.isControl()) return;
	if (c.getTG() == tg) return;

	c.setTG(tg);
	talkgroups.updateUI();
    };

    this.channelLevels = function(response) {
	var levels = response.levels;
	for (var f in levels) {
	    var c = channelIndex[f];
	    if (!c) continue;

	    c.setLevel(levels[f]);
	}
    };

    this.channelStates = function(response) {
	var squelch = response.squelch;
	var states = response.states;

	for (var f in states) {
	    var r = states[f];
	    var level = r[0];
	    var tg = r[1];

	    var c = channelIndex[f];
	    if (!c) continue;

	    c.setTG(tg);
	    c.setLevel(level, squelch);
	}
    };

    var tg_channels = function(tg) {
	return channels.filter(function(e,i,a) { return e.getTG() == tg;});
    }
    this.tgChannels = tg_channels;

    this.tgXmitting = function(tg) {
	var assigned_channels = tg_channels(tg);

	return assigned_channels.some(function(e,i,a) { return e.isXmit(); })
    }

    return this;
}
