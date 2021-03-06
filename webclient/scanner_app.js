function ScannerApp() {
    var hostname = document.location.hostname;

    //////////////////////////////////////////
    // The actual websocket connection
    var scanner_connection = new ScannerConnection();

    // Some goofy gymnastics to ensure we're always trying to reconnect
    function scanner_reconnect() { 
	if (scanner_connection.reconnect(hostname)) {
	    window.setTimeout(scanner_reconnect, 4000);
	}
    }

    scanner_connection.register("_CLOSE_", 
			       function() { 
			           window.setTimeout(scanner_reconnect, 
						     4000);
                               });

    scanner_connection.updateUI();
    window.setInterval(scanner_connection.updateUI, 1000);


    var scanner_settings = new ScannerSettings();
    scanner_settings.loadFromCookie();

    //////////////////////////////////////////
    // stack configuration
    //
    var scanner_config = new ScannerConfig();
    scanner_connection.register("config", scanner_config.updateConfig);

    //////////////////////////////////////////
    // Talkgroup decoder ring
    //
    var scanner_talkgroups = new ScannerTalkgroups();
    scanner_talkgroups.attachSettings(scanner_settings);
    scanner_config.register(scanner_talkgroups.configUpdate);


    //////////////////////////////////////////
    // Audio player
    //
    var scanner_player = new ScannerPlayer();
    scanner_player.updateUI();

    scanner_player.registerTalkgroups(scanner_talkgroups);

    scanner_config.register(scanner_player.configUpdate);

    scanner_connection.register("fileup", scanner_player.handle_fileup);
    scanner_connection.register("tgfile", scanner_player.handle_tgfile);



    //////////////////////////////////////////
    // Channel status display
    //
    var channel_board = new ChannelBoard();
    channel_board.registerTalkgroups(scanner_talkgroups);

    scanner_config.register(channel_board.configUpdate);

    scanner_talkgroups.registerChannelBoard(channel_board);

    scanner_connection.register("start", channel_board.channelStart);
    scanner_connection.register("stop", channel_board.channelStop);
    scanner_connection.register("tune", channel_board.channelTag);
    scanner_connection.register("levels", channel_board.channelLevels);
    scanner_connection.register("states", channel_board.channelStates);


    //////////////////////////////////////////
    // All set up: time to go!

    scanner_reconnect(hostname);

    this.settings = scanner_settings;
    this.connection = scanner_connection;
    this.config = scanner_config;
    this.player = scanner_player;
    this.talkgroups = scanner_talkgroups;
    this.channel_board =  channel_board;

    return this;
}
