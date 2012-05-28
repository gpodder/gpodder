
gPodder = {
    /* XXX: Partially ugly. Some parts would be shorter with JQuery. */

    currentlySelectedPodcast: null,
    currentlySelectedEpisode: null,

    quote: function(str) {
        var s = String(str);
        s = s.replace(/&/g, '&amp;');
        s = s.replace(/</g, '&lt;');
        s = s.replace(/>/g, '&gt;');
        s = s.replace(/"/g, '&quot;');
        return s;
    },

    url: {
        podcasts: '/json/podcasts.json',
        episodes: function(podcast) {
            return '/json/podcast/' + podcast.id + '/episodes.json';
        },
    },

    createEpisode: function(episode) {
        var li = document.createElement('li');
        var a = document.createElement('a');
        a.setAttribute('gpodder:episode', JSON.stringify(episode));
        a.href = '#episode_details';
        a.onclick = function() {
            gPodder.selectEpisode(this);
            gPodder.currentlySelectedEpisode = this;
        };
        li.appendChild(a);
        a.appendChild(document.createTextNode(episode.title));
        return li;
    },

    createPodcast: function(podcast) {
        var li = document.createElement('li');
        var a = document.createElement('a');
        a.setAttribute('gpodder:podcast', JSON.stringify(podcast));
        a.href = '#episodes_page';
        a.onclick = function() {
            gPodder.selectPodcast(this);
            gPodder.currentlySelectedPodcast = this;
        };
        li.appendChild(a);
        a.appendChild(document.createTextNode(podcast.title));
        return li;
    },

    init: function() {
        var xmlhttp = new XMLHttpRequest();
        var podcasts_ul = document.getElementById('podcasts');
        xmlhttp.onreadystatechange = function() {
            if (xmlhttp.readyState == 4) {
                podcasts_ul.innerHTML = '';

                var podcasts = JSON.parse(xmlhttp.responseText);
                var lis = podcasts.map(gPodder.createPodcast);
                for (i=0; i<lis.length; i++) {
                    podcasts_ul.appendChild(lis[i]);
                }
                $('#podcasts').listview('refresh');
            }
        };
        xmlhttp.open('GET', gPodder.url.podcasts, true);
        xmlhttp.send(null);
    },

    selectPodcast: function(li) {
        var podcast = JSON.parse(li.getAttribute('gpodder:podcast'));

        var xmlhttp = new XMLHttpRequest();
        var episodes_ul = document.getElementById('episodes');
        xmlhttp.onreadystatechange = function() {
            if (xmlhttp.readyState == 4) {
                episodes_ul.innerHTML = '';
                $('#episodes_title').html(podcast.title);

                var episodes = JSON.parse(xmlhttp.responseText);
                var lis = episodes.map(gPodder.createEpisode);
                for (i=0; i<lis.length; i++) {
                    episodes_ul.appendChild(lis[i]);
                }
                $('#episodes').listview('refresh');
            }
        };
        xmlhttp.open('GET', gPodder.url.episodes(podcast), true);
        xmlhttp.send(null);
    },

    selectEpisode: function(li) {
        var episode = JSON.parse(li.getAttribute('gpodder:episode'));
        var content = '';
        var media_url = '';

        var keys = new Array();
        for (var key in episode) {
            keys.push(key);
        }
        keys.sort();

        for (var i=0; i<keys.length; i++) {
            var data = episode[keys[i]];

            if (keys[i] === 'url') {
                content += '<audio controls="controls"><source src="' + data + '" type="audio/mp3" /></audio><br>';
            }

            if (data !== null && data.length !== undefined && data.length > 50) {
                data = data.substring(0, 48) + '...';
            }
            var key = gPodder.quote(keys[i]);
            var data = gPodder.quote(data);
            content += '<strong>' + key + '</strong> = ' + data + '<br>';
        }

        $('#episode_details_content').html(content);
    },

};

