function ScannerApp() {
    var hostname = document.location.hostname;

    //////////////////////////////////////////
    // The actual websocket connection
    var scanner_connection = new ScannerConnection();
    scanner_connection.attachUI($("#connstatus"));

    function scanner_reconnect() {scanner_connection.connect(hostname); }

    scanner_connection.register("_CLOSE_", 
			       function() { 
			           window.setTimeout(scanner_reconnect, 
						     4000);
                               });

    scanner_connection.updateUI();
    window.setInterval(scanner_connection.updateUI, 500);


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
    scanner_talkgroups.attachTGDiv($("#talkgroupboard"));
    scanner_talkgroups.attachSettings(scanner_settings);
    scanner_config.register(scanner_talkgroups.configUpdate);


    //////////////////////////////////////////
    // Audio player
    //
    var scanner_player = new ScannerPlayer();

    scanner_player.initUI($("#nowplaying"));
    scanner_player.registerTalkgroups(scanner_talkgroups);

    scanner_config.register(scanner_player.configUpdate);

    scanner_connection.register("fileup", scanner_player.handle_fileup);
    scanner_connection.register("tgfile", scanner_player.handle_tgfile);



    //////////////////////////////////////////
    // Channel status display
    //
    var channel_board = new ChannelBoard();
    channel_board.attachUI($("#channelboard"));
    channel_board.registerTalkgroups(scanner_talkgroups);

    scanner_config.register(channel_board.configUpdate);

    scanner_talkgroups.registerChannelBoard(channel_board);

    scanner_connection.register("start", channel_board.channelStart);
    scanner_connection.register("stop", channel_board.channelStop);
    scanner_connection.register("tune", channel_board.channelTag);
    scanner_connection.register("levels", channel_board.channelLevels);


    //////////////////////////////////////////
    // All set up: time to go!

    scanner_connection.connect(hostname);

    this.settings = scanner_settings;
    this.connection = scanner_connection;
    this.config = scanner_config;
    this.player = scanner_player;
    this.talkgroups = scanner_talkgroups;
    this.channel_board =  channel_board;

    return this;
}
