function Channel(entry) {
    var frequency = entry.freq;
    var is_control = entry.is_control;
    var name = entry.name;
    var level = -100;
    var xmitting = false;

    var div_id = "channel_" + parseInt(entry.freq);
    var ui = new ScannerTemplate("#" + div_id, $("#tmpl_channel_status"), 
                                 function() {
	                             var display_hover = function() {
	                                 $(this).find(".channel_hover").fadeIn(100);
	                             };
                                     
	                             var hide_hover = function() {
	                                 $(this).find(".channel_hover").fadeOut(200);
	                             };

	                             $(this).hover(display_hover, hide_hover);
                                 });



    var config = null;
    this.configUpdate = function(newconfig) { config = newconfig; }
    var tg = 0;
    this.setTG = function(v) { tg = v; updateUI();}

    this.getTG = function() { return tg; };

    var talkgroups = null;

    this.getFrequency = function() { return frequency; }
    this.isControl = function() { return is_control; }
    this.getName = function() { return name; }
    
    this.isXmit = function() { return xmitting; }


    var decode_talkgroup = function(tg) {
	if (!talkgroups) return null;
	return talkgroups.lookup(tg);
    }


    var template_data = function() {
	var data = {};
	var disptring = ""

	data["channel_freq"] = frequency;
	data["xmitting"] = xmitting;
	data["channel_level_class"] = "channel_xmit_-_" + (data["xmitting"] ? "yes" : "no");
	data["channel_status_class"] = "channel_row_xmit_-_" + (data["xmitting"] ? "yes" : "no");

	data["channel_tg_idno"] = parseInt(tg).toString(16);
	
	var curTG = talkgroups.lookup(tg);
	data["channel_tg_category"] = curTG ? curTG.category() : "-";
	data["channel_tg_short"] = curTG ? curTG.short() : "unk";
	data["channel_tg_long"] = curTG ? curTG.long() : "[Unknown]";
	data["channel_level"] = parseInt(level);
	if (data["level"] > 0) data["level"] = "+" + data["level"];

	if (data["level"] < -99) data["level"] = ""; // don't show -100s

	data["following"] = talkgroups.following(tg) ? "tg_followed" : "tg_nofollow";

	data["channel_div_id"] = div_id;

	if (is_control) { // TODO refactor control_counts to attach here
	    data["is_control"] = true;
	    data["channel_tg_idno"] = "-";
	    data["channel_tg_short"] = "control";
	    data["channel_tg_long"] = " - control -";
	    data["following"] = "tg_control";
	}

	return data;
    }
    this.template_data = template_data;

    var updateUI = function() {
        var data = template_data();
        ui.update(data);
    };
    this.updateUI = updateUI;

    this.setLevel = function(l, squelch) { 
	level = l; 
	if (squelch) xmitting = (level > squelch);
	updateUI(); 
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
    var channels = [];

    var channelIndex = {};
    this.channels = channels;
    this.channelIndex = channelIndex;
    var talkgroups = null;

    this.registerTalkgroups = function(tgs) { 
	talkgroups = tgs; 
	channels.forEach(function(c) { c.registerTalkGroups(tgs) });
    };

    var updateUI = function() {
        channels.forEach(function(e) { e.updateUI(); });
    }

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

	var alldata = channels.map(function(e,i,a) { return e.template_data(); });
	$("#channellist").loadTemplate("#tmpl_channel_status_dummy", alldata);


	updateUI();
	return;
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
	talkgroups.updateUI();
    };

    var baseTG = function(tg) { return parseInt(tg) - parseInt(tg)%16; };

    var tg_channels = function(tg) {
	return channels.filter(function(e,i,a) { return baseTG(e.getTG()) == baseTG(tg);});
    }
    this.tgChannels = tg_channels;

    this.tgXmitting = function(tg) {
	var assigned_channels = tg_channels(tg);

	return assigned_channels.some(function(e,i,a) { return e.isXmit(); })
    }

    return this;
}
