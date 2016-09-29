function ScannerTalkgroup(d, cb) {
    var tgid = d.tg;
    var category = d.category;
    this.category = function() { return category; };
    var short = d.short;
    this.short = function() { return short; };
    var long = d.long;
    this.long = function() { return long; };

    var channel_board = cb;

    this.tg = tgid;

    var div_id = "talkgroup_" + parseInt(tgid).toString(16);

    //////////////////////
    // Are we following this TG?
    var followed = false;
    this.following = function() { return followed; }

    var toggleFollow = function() {
	followed = (!followed);
	updateUI();
    };
    this.toggleFollow = toggleFollow;

    var setFollow = function(b) { followed = b; }
    this.setFollow = setFollow;

    //////////////////////
    // A list of channels this TG is transmitting on
    var transmitting = []; // list of channels on which we're transmitting
    this.channelOpen = function(freq) {
	if (-1 != transmitting.indexOf(freq)) return;
	transmitting.push(freq);
    }

    this.channelClose = function(freq) {
	if (-1 == transmitting.indexOf(freq)) return;
	transmitting.slice(transmitting.indexOf(freq),1);
    }

    //////////////////////////////////////////////////////////////////////
    // A list of recent WAVs for this TG
    var wavs = []; // list of ScannerPlayer events, e.tg == tg, e.path = wav, etc.


    //////////////////////////////////////////////////////////////////////
    // Is this currently filtered out of the display?
    var filtered = false;
    var filtered_xmit = false;
    var filtered_followed = false;

    var setFiltered = function(v, xmit_only, follow_only) { 
	filtered = v;

	filtered_xmit = xmit_only;
	filtered_followed = follow_only;

	updateUI();
    }
    this.setFiltered = setFiltered;

    var get_desc = function() {
	return tgid.toString(16) + " " + category + " " + short + " " + long;
    }

    this.applyFilter = function(filter_str, xmit_only, follow_only) {
	var curdesc_lc = get_desc().toLowerCase();
	var filter_lc = filter_str.toLowerCase();

	var is_filtered = (-1 == curdesc_lc.indexOf(filter_lc));
	setFiltered(is_filtered, xmit_only, follow_only);
	return checkFiltered();
    };

    var checkFiltered = function() {
	if (filtered) return true;
	if (filtered_xmit && !(cb.tgXmitting(tgid))) return true;
	if (filtered_followed && !followed) return true;

	return false;
    };

    //////////////////////
    // Actual data render
    var template_data = function() {
	var data = {};

	data["talkgroup_div_id"] = div_id;
	data["talkgroup_xmit_class"] = cb.tgXmitting(tgid) ? "channel_xmit" : "channel_idle";
	data["tg_idno"] = tgid.toString(16);
	data["following"] = (followed ? "tg_followed" : "tg_nofollow");
	data["level"] = "";
	data["tg_category"] = category;
	data["short"] = short;
	data["long"] = long;
	data["filtered"] = checkFiltered() ? "tg_filtered" : "tg_unfiltered";

	data["cum_class"] = data["filtered"] + " " + data["talkgroup_xmit_class"] + " " + data["following"];

	return data;
    };
    this.template_data = template_data;

    var updateUI = function() {
	$("#" + div_id).loadTemplate("#tmpl_tg_status", template_data());
    };
    this.updateUI = updateUI;

    this.addClick = function() {
	$("#" + div_id).click(function() { toggleFollow(); });
    };
    
    return this;
}


function ScannerTalkgroups() {
    var tgs = [];
    var tgIndex = {}; // tg => entry

    var tg_filter_string = ""; // filter tg list on this
    

    //////////////////////
    // Help out the channel display
    var channel_board = null;
    this.registerChannelBoard = function(chanb) { channel_board = chanb; };

    var baseTG = function(tg) { return parseInt(tg) - parseInt(tg) % 16; }

    var following = function(tgid) {
	try {
	    return tgIndex[baseTG(tgid)].following();
	} catch(e) {
	    return false;
	}
    };
    this.following = following;


    //////////////////////
    // Settings, to save between sessions
    var settings = null;
    var updateSettings = function() {
	var tg_follows = [];
	for (var t in tgs) {
	    if (t.following())
		tg_follows.push(t.tg);
	}
	settings.set("talkgroups.follow", tg_follows);
    }

    var attachSettings = function(scanner_settings) {
	settings = scanner_settings;
	var settings_followed =  settings.get("talkgroups.follow");

	if (settings_followed) {
	    var tg_follows = settings_followed;
	    for (t in tg_follows) {
		if (tgIndex[t]) tgIndex[t].setFollow(true);
	    }
	}
    };
    this.attachSettings = attachSettings;


    //////////////////////
    // Update the UI
    var applyFilter = function() {
	var filter_str = $("#tg_filter_input").val();
	var filter_xmit_only = $("#tg_filter_cb_xmit").is(":checked");
	var filter_follow_only = $("#tg_filter_cb_follow").is(":checked");

	var n_filtered = 0;

	tgs.forEach(function(t) {
	    if (t.applyFilter(filter_str, filter_xmit_only, filter_follow_only)) {
		n_filtered++;
	    }
	});
	console.log("Filtered " + n_filtered + " entries");
    }
    this.applyFilter = applyFilter;

    this.updateUI = function(){ tgs.forEach(function(t) { t.updateUI(); }) }

    $("#tg_filter_input").change(function() { applyFilter(); });
    $("#tg_filter_input").keyup(function() { applyFilter(); });

    $("#tg_filter_cb_xmit").change(function() { applyFilter(); });
    $("#tg_filter_cb_follow").change(function() { applyFilter(); });



    this.configUpdate = function(config) {
	var dicts = config["talkgroups"];
	tgs = dicts.map(function(e) { return new ScannerTalkgroup(e, channel_board); });

	tgs.sort(function(a,b) { return (a.tg < b.tg ? -1 : 1); });

	tgIndex = {}
	tgs.forEach(function(t) { tgIndex[t.tg] = t; });

	var datas = tgs.map(function(e) { return e.template_data(); });
	$("#talkgrouplist").loadTemplate($("#tmpl_tg_status"), datas);
	tgs.forEach(function(e) { e.addClick(); })
    }

    this.lookup = function(tg) {
	var base_tg = parseInt(tg);
	base_tg -= base_tg % 16;
	return tgIndex[base_tg];
    }


    return this;
}
