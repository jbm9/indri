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
    var ui = new ScannerTemplate("#"+div_id, $("#tmpl_tg_status"));

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


    var get_desc = function() {
	return tgid.toString(16) + " " + category + " " + short + " " + long;
    }

    //////////////////////////////////////////////////////////////////////
    // Is this currently filtered out of the display?
    var filtered = false;
    var filtered_xmit = false;
    var filtered_followed = false;

    this.applyFilter = function(filter_str, xmit_only, follow_only) {
	var curdesc_lc = get_desc().toLowerCase();
	var filter_lc = filter_str.toLowerCase();

	var is_filtered = (-1 == curdesc_lc.indexOf(filter_lc));
        filtered = is_filtered;
        filtered_xmit = xmit_only;
        filtered_followed = follow_only;

        updateUI();

	return checkFiltered();
    };

    var checkFiltered = function() {
	if (filtered) return true;
	if (filtered_xmit && !(cb.tgXmitting(tgid))) return true;
	if (filtered_followed && !followed) return true;

	return false;
    };
    this.checkFiltered = checkFiltered;

    //////////////////////
    // Actual data render
    var template_data = function() {
	var data = {};

	data["talkgroup_div_id"] = div_id;

	data["talkgroup_filter_class"] = "talkgroup_tg_filtered_-_" + (checkFiltered() ? "yes" : "no");
	data["talkgroup_following_class"] = "talkgroup_tg_following_-_" + (followed ? "yes" : "no");
	data["talkgroup_xmit_class"] = "talkgroup_xmit_-_" + (cb.tgXmitting(tgid) ? "yes" :"no");

	data["talkgroup_tg_idno"] = tgid.toString(16);
	data["talkgroup_tg_category"] = category;
	data["talkgroup_tg_short"] = short;
	data["talkgroup_tg_long"] = long;

	// data["cum_class"] = data["filtered"] + " " + data["talkgroup_xmit_class"] + " " + data["following"];

	return data;
    };
    this.template_data = template_data;

    var lastdata = {};

    var updateUI = function() {
        var data = template_data();

        ui.update(data);
        return;

        var do_update = false;

        for (var k in data) {
            if (data[k] != lastdata[k]) {
                do_update = true;
                break;
            }
        }
        lastdata = data;

        if (!do_update) return;

        uidiv = apply_template(uidiv,
                               data,
                               $("#" + div_id),
                               $("#tmpl_tg_status"),
                               function() {});
        return; 
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
