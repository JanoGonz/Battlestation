{{ moment.include_moment() }}
{{ moment.lang(g.locale) }}

function set_message_count(n) {
    $('#message_count').text(n);
    $('#message_count').css('visibility', n ? 'visible' : 'hidden');
}
$(document).ready(function () {
    var since = 0;
    var original_title = document.title;
    setInterval(function () {
        $.ajax("{{ url_for('main.notifications') }}?since=" + since).done(
            function (notifications) {
                for (var i = 0; i < notifications.length; i++) {
                    if (notifications[i].name == 'unread_message_count')
                        set_message_count(notifications[i].data);
                    if (notifications[i].data > 0) {
                        document.title = "(" + notifications[i].data + ") " + original_title;
                    }
                    since = notifications[i].timestamp;

                }
            }
        );
    }, 10000);
});