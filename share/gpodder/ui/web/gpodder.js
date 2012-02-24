
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
        li.setAttribute('gpodder:episode', JSON.stringify(episode));
        li.onclick = function() {
            if (gPodder.currentlySelectedEpisode !== null) {
                var e = gPodder.currentlySelectedEpisode;
                e.innerHTML = gPodder.quote(JSON.parse(e.getAttribute('gpodder:episode')).title);
                gPodder.currentlySelectedEpisode.setAttribute('class', '');
            }
            gPodder.selectEpisode(this);
            gPodder.currentlySelectedEpisode = this;
            this.setAttribute('class', 'selected');
        };
        li.appendChild(document.createTextNode(episode.title));
        return li;
    },

    createPodcast: function(podcast) {
        var li = document.createElement('li');
        li.setAttribute('gpodder:podcast', JSON.stringify(podcast));
        li.onclick = function() {
            if (gPodder.currentlySelectedPodcast !== null) {
                gPodder.currentlySelectedPodcast.setAttribute('class', '');
            }
            gPodder.selectPodcast(this);
            gPodder.currentlySelectedPodcast = this;
            this.setAttribute('class', 'selected');
        };
        li.appendChild(document.createTextNode(podcast.title));
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

                var episodes = JSON.parse(xmlhttp.responseText);
                var lis = episodes.map(gPodder.createEpisode);
                for (i=0; i<lis.length; i++) {
                    episodes_ul.appendChild(lis[i]);
                }
            }
        };
        xmlhttp.open('GET', gPodder.url.episodes(podcast), true);
        xmlhttp.send(null);
    },

    selectEpisode: function(li) {
        var episode = JSON.parse(li.getAttribute('gpodder:episode'));
        li.innerHTML = '';

        var keys = new Array();
        for (var key in episode) {
            keys.push(key);
        }
        keys.sort();

        for (var i=0; i<keys.length; i++) {
            var data = episode[keys[i]];
            if (data !== null && data.length !== undefined && data.length > 50) {
                data = data.substring(0, 48) + '...';
            }
            var key = gPodder.quote(keys[i]);
            var data = gPodder.quote(data);
            li.innerHTML += '<strong>' + key + '</strong> = ' + data + '<br>';
        }
    },

};

