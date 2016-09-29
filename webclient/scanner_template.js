/*
 * jquery loadTemplate is really nice, but we wind up spamming it a
 * lot with constantly refreshing content.  This winds up chewing up
 * _lots_ of CPU, which is unfortunate.  To avoid that, we're going to
 * do some nasty awkward kludging, as I don't see a way to do live
 * updates within the loadTemplate framework (but, to be fair, my
 * javascript is not super strong, so there may be something exposed
 * out the side that I missed.
 *
 * To do this, we abuse the namespace a bit: all data-content fields
 * should shadow a class attribute of the element; for text
 * replacement, we then just go through and find .foo values and tack
 * in the data["foo"] value in their text.
 *
 * This gets hairy when we want to change the class,
 * though. Specifically, we usually want to toggle a class between
 * "in-transmission" and "channel idle" or thereabouts.  To do this,
 * we need to delete old values, but we don't know what they are
 * a-priori. First, we tag all class-wise values as "foo_class" in the
 * name; if you have any data-content values that end in "foo_class,"
 * sorry, you need to change them. Then, to tell which classes to
 * remove, we ensure that the class values are delimited fields, of
 * the form channel_xmit_-_yes.  We then go through the class list of
 * every target element and delete any classes that start with
 * channel_xmit_-_, and then add our own later.
 *
 * Astonishingly, this code seems to work.
 *
 * This also allows us to get rid of accumulating classes ourselves to
 * feed into loadTemplate, and instead just set classes individually.
 */

function apply_template() {}

function ScannerTemplate(target, template, creation_cb) {
    var lastdata = {};
    var uidiv = null;
    
    function update(data) {
        if (!uidiv) {
            $(target).loadTemplate(template, data);
            if (creation_cb) creation_cb.call($(target));

            uidiv = $(target);
            return;
        }

        for (var k in data) {
            if (data[k] == lastdata[k]) continue;

            // classes are awkward: we only allow one at a time
            if (k.substr(-5) == "class") {
                var classname = data[k];
                var classbase = classname.substr(0, classname.indexOf("_-_")+3); // include _-_
                var cb_len = classbase.length;

                var targets = uidiv.find("." + k.substr(0,k.length-6));

                for (var i = 0; i < targets.length; i++) {
                    var applied_classes = targets[i].className.split(" ");
                    var to_remove = applied_classes.filter(
                        function(e) { return e.substr(0, cb_len) == classbase; }
                    );

                    to_remove.forEach(function(e) { $(targets[i]).removeClass(e) });
                }
                targets.addClass(classname);


            } else {
                // Ah, finally, trivial text-replacement.
                uidiv.find("." + k).text(data[k]);
            }
        }
        lastdata = data;
        return;
    };
    this.update = update;


    return this;
};
