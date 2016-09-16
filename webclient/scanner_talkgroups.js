function ScannerTalkgroups() {
    var tgs = [];
    var tgIndex = {}; // tg => entry

    var tg_follows = []; // list of tgIDs we're following

    var tgdiv = null; // <div> for the talkgroup selector
    var listdiv = null; // <div> for the tg list itself

    var tg_filter_string = ""; // filter tg list on this

    var channel_board = null;

    this.registerChannelBoard = function(chanb) { channel_board = chanb; };

    var following = function(tg) {
	return -1 != tg_follows.indexOf(tg);
    };
    this.following = following;

    this.follows = function() { return tg_follows; };


    var follow_talkgroup = function(tg, skip_update) {
	if (-1 != tg_follows.indexOf(tg)) return;
	tg_follows.push(tg);
	if (!skip_update) updateUI();
    };
    this.followTalkgroup = follow_talkgroup;

    var unfollow_talkgroup = function(tg, skip_update) {
	var i = tg_follows.indexOf(tg);
	if (-1 == tg_follows) return;
	tg_follows.splice(i,1);
	if (!skip_update) updateUI();
    };
    this.unfollowTalkgroup = unfollow_talkgroup;

    var toggle_talkgroup = function(tg) {
	if (following(tg)) unfollow_talkgroup(tg);
	else follow_talkgroup(tg);
    }


    var initUI = function() {
	listdiv.empty();
	listdiv.append($("<div id='tg_stand_in_div' class='tg_filtered'>"));
    	tgs.forEach(function(e,i,a) {
	    var desc = e.tg.toString(16) + " : " + e.category + "/" + e.short + ": " + e.long;
 	    var curdiv = $("<div id='tg_box_" + e.tg + "'>");
	    curdiv.text(desc);

	    curdiv.click(function() { toggle_talkgroup(e.tg); });

	    listdiv.append(curdiv);
	});
    }
	
	 
    var updateUI = function() {
	var n_filtered = 0;
	var filtered_xmit = false;
	var filtered_follow = false;

	tgs.forEach(function(e,i,a) {
 	    var curdiv = $("#tg_box_" + e.tg);
	    if (!curdiv) {
		console.log("Missing div for tg=" + e.tg);
		return;
	    }

	    var is_xmitting = channel_board.tgXmitting(e.tg);

	    var desc = e.tg.toString(16) + " : " + e.category + "/" + e.short + ": " + e.long;
	    var is_filtered = (-1 == desc.indexOf(tg_filter_string));

	    if (is_filtered) n_filtered += 1;

	    curdiv.toggleClass("tg_filtered", is_filtered);

	    if (following(e.tg)) {
		curdiv.addClass("tg_followed");
		if (is_filtered) filtered_follow = true;
	    } else {
		curdiv.removeClass("tg_followed");
	    }

	    if (channel_board.tgXmitting(e.tg)) {
		curdiv.addClass("tg_transmitting");
		if (is_filtered) filtered_xmit = true;
	    } else {
		curdiv.removeClass("tg_transmitting");
	    }
	});

	var stand_in_div = $("#tg_stand_in_div");
	stand_in_div.text(" - Filtered " + n_filtered + " TGs with '" + tg_filter_string + "'")
	if (filtered_xmit) stand_in_div.addClass("tg_transmitting");
	if (filtered_follow) stand_in_div.addClass("tg_follwed");

	stand_in_div.toggleClass("tg_filtered", n_filtered == 0);

    }
    this.updateUI = updateUI;

    this.attachTGDiv = function(tgdiv_in) {
	tgdiv = $(tgdiv_in);

	var filterdiv = $("<div>");
	var filter_box = $("<input>");
	filterdiv.append(filter_box);
	tgdiv.append(filterdiv);

	filter_box.change(function() {
	    tg_filter_string = this.value;
	    updateUI();
	});

	listdiv = $("<div>")
	tgdiv.append(listdiv);

	initUI();

	updateUI();
    };


    this.configUpdate = function(config) {
	tgs = config["talkgroups"];

	tgs.sort(function(a,b) { return (a.tg < b.tg ? -1 : 1); });

	tgIndex = {}
	tgs.forEach(function(t) { tgIndex[t.tg] = t; });

	channelStates = {};
	
	initUI();
	updateUI();
    }

    this.lookup = function(tg) {
	return tgIndex[tg];
    }


    return this;
}
