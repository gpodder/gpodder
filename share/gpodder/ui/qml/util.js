
function formatDuration(duration) {
    var h = parseInt(duration / 3600) % 24
    var m = parseInt(duration / 60) % 60
    var s = parseInt(duration % 60)

    var hh = h > 0 ? (h < 10 ? '0' + h : h) + ':' : ''
    var ms = (m < 10 ? '0' + m : m) + ':' + (s < 10 ? '0' + s : s)

    return hh + ms
}

function formatCoverURL(podcast) {
    var cover_file = podcast.qcoverfile;
    var cover_url = podcast.qcoverurl;
    var podcast_url = podcast.qurl;
    var podcast_title = podcast.qtitle;

    return ('image://cover/' + escape(cover_file) + '|' +
        escape(cover_url) + '|' + escape(podcast_url) + '|' +
        escape(podcast_title));
}

