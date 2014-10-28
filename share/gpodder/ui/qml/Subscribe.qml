
import QtQuick 1.1

import org.gpodder.qmlui 1.0
import com.nokia.meego 1.0

import 'config.js' as Config

Item {
    id: subscribe

    signal subscribe(variant urls)

    function show() {
        searchInput.text = ''
        searchResultsListModel.clear();
        resultsSheet.reject();
        directoryButtons.reloadOptions();
    }

    function search() {
        var q = searchInput.text;

        var direct_prefixes = [
            // See src/gpodder/util.py, normalize_feed_url(), this
            // should be kept in sync if new prefixes are added
            'http://', 'https://', 'fb:', 'yt:', 'sc:', 'ytpl:'
        ];

        for (var i=0; i<direct_prefixes.length; i++) {
            if (q.indexOf(direct_prefixes[i]) === 0) {
                /* Directly subscribe to a URL */
                subscribe.subscribe([q]);
                return;
            }
        }

        /* Search the web directory */
        searchResultsListModel.search(q);
        resultsSheet.open();
    }

    onVisibleChanged: {
        if (!visible) {
            searchInput.closeVirtualKeyboard()
            listView.selectedIndices = []
        }
    }

    Item {
        id: topBar
        visible: resultsSheet.status == DialogStatus.Closed
        height: 70

        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
        }

        InputField {
            id: searchInput
            placeholderText: _('Search term or URL')

            anchors {
                leftMargin: Config.smallSpacing
                left: parent.left
                right: searchButton.left
                verticalCenter: parent.verticalCenter
            }

            onAccepted: subscribe.search()
            actionName: _('Search')
        }

        SimpleButton {
            id: searchButton
            image: 'artwork/search.png'

            onClicked: subscribe.search()

            width: parent.height
            height: parent.height

            anchors {
                top: parent.top
                right: parent.right
            }
        }
    }

    ListView {
        id: directoryButtons
        visible: topBar.visible
        clip: true

        anchors {
            left: parent.left
            right: parent.right
            top: topBar.bottom
            bottom: parent.bottom
            topMargin: Config.smallSpacing
        }

        model: ListModel { id: directoryButtonsModel }

        function doAction(action) {
            if (action === 'toplist') {
                searchResultsListModel.loadJson('https://gpodder.net/toplist/50.json');
                resultsSheet.open();
            } else if (action === 'mygpo') {
                if (controller.myGpoEnabled) {
                    searchResultsListModel.loadJson('https://' + controller.myGpoUsername + ':' + controller.myGpoPassword + '@gpodder.net/subscriptions/' + controller.myGpoUsername + '.json');
                    resultsSheet.open();
                }
            } else if (action === 'suggestions') {
                if (controller.myGpoEnabled) {
                    searchResultsListModel.loadJson('https://' + controller.myGpoUsername + ':' + controller.myGpoPassword + '@gpodder.net/suggestions/50.json');
                    resultsSheet.open();
                }
            } else {
                // Assume action is a URL
                searchResultsListModel.loadJson(action);
                resultsSheet.open();
            }
        }

        Component.onCompleted: {
            reloadOptions();
        }

        function reloadOptions() {
            directoryButtonsModel.clear();
            directoryButtonsModel.append({label: _('Most-subscribed on gpodder.net'), action: 'toplist'});

            if (controller.myGpoEnabled) {
                directoryButtonsModel.append({label: _('Your subscriptions on gpodder.net'), action: 'mygpo'});
                directoryButtonsModel.append({label: _('Recommended by gpodder.net for you'), action: 'suggestions'});
            }

            var result = new XMLHttpRequest();
            result.onreadystatechange = function() {
                if (result.readyState == XMLHttpRequest.DONE) {
                    var data = JSON.parse(result.responseText);
                    data.sort(function (a, b) {
                        // Sort by usage count, descending
                        return b.usage - a.usage;
                    });
                    for (var i=0; i<data.length; i++) {
                        directoryButtonsModel.append({label: data[i].tag, action: 'https://gpodder.net/api/2/tag/' + data[i].tag + '/50.json'});
                    }
                }
            };
            result.open('GET', 'https://gpodder.net/api/2/tags/50.json');
            result.send();
        }

        delegate: SelectableItem {
            property variant modelData: undefined

            Label {
                text: label

                anchors {
                    left: parent.left
                    right: parent.right
                    verticalCenter: parent.verticalCenter
                    margins: Config.smallSpacing
                }

                elide: Text.ElideRight
            }

            onSelected: {
                directoryButtons.doAction(action);
            }
        }
    }

    ScrollScroll {
        flickable: directoryButtons
        visible: directoryButtons.visible
    }


    Sheet {
        id: resultsSheet

        anchors.fill: parent
        anchors.topMargin: (width > height || status == DialogStatus.Closed) ? 0 : -50 // see bug 1915

        acceptButtonText: _('Subscribe')
        rejectButtonText: _('Cancel')

        content: Item {
            anchors.fill: parent

            MouseArea {
                anchors.fill: parent
                onClicked: console.log('caught')
            }

            ListView {
                id: listView
                property variant selectedIndices: []

                opacity: searchResultsListModel.loaded ? 1 : 0
                Behavior on opacity { PropertyAnimation { } }

                anchors.fill: parent

                model: ListModel {
                    id: searchResultsListModel
                    property bool loaded: false

                    function search(query) {
                        loadJson('https://gpodder.net/search.json?q=' + query);
                    }

                    function loadJson(url) {
                        clear();
                        searchResultsListModel.loaded = false;

                        var result = new XMLHttpRequest();
                        result.onreadystatechange = function() {
                            if (result.readyState == XMLHttpRequest.DONE) {
                                var data = JSON.parse(result.responseText);
                                data.sort(function (a, b) {
                                    // Sort by subscriber count, descending
                                    return b.subscribers - a.subscribers;
                                });
                                for (var i=0; i<data.length; i++) {
                                    searchResultsListModel.append(data[i]);
                                }
                                searchResultsListModel.loaded = true;
                            }
                        };

                        result.open('GET', url);
                        result.send();
                    }
                }

                delegate: SelectableItem {
                    id: subscribeDelegate
                    property string modelData: url
                    inSelection: (listView.selectedIndices.indexOf(index) != -1)

                    height: Config.listItemHeight
                    width: listView.width

                    Item {
                        id: coverArt

                        height: Config.listItemHeight
                        width: Config.listItemHeight

                        anchors {
                            leftMargin: Config.largeSpacing
                            left: parent.left
                            verticalCenter: parent.verticalCenter
                        }

                        Image {
                            anchors.centerIn: parent
                            source: scaled_logo_url
                        }
                    }

                    Column {
                        anchors {
                            leftMargin: Config.largeSpacing
                            rightMargin: Config.largeSpacing
                            left: coverArt.right
                            right: parent.right
                            verticalCenter: parent.verticalCenter
                        }

                        Label {
                            id: subscribeDelegateTitle
                            text: title + ' (' + subscribers + ')'
                            anchors.leftMargin: Config.largeSpacing
                            color: !subscribeDelegate.inSelection?'white':Config.selectColor
                            font.pixelSize: 25
                        }

                        Label {
                            text: url
                            anchors.leftMargin: Config.largeSpacing
                            color: subscribeDelegateTitle.color
                            font.pixelSize: 15
                        }
                    }

                    onSelected: {
                        var position = listView.selectedIndices.indexOf(index);
                        var tmp;
                        var i;

                        tmp = new Array();

                        for (i=0; i<listView.selectedIndices.length; i++) {
                            if (listView.selectedIndices[i] != index) {
                                tmp.push(listView.selectedIndices[i]);
                            }
                        }

                        if (position == -1) {
                            tmp.push(index);
                        }

                        listView.selectedIndices = tmp;
                    }
                }
            }

            ScrollScroll {
                flickable: listView
            }

            BusyIndicator {
                anchors.centerIn: parent
                running: opacity > 0

                opacity: searchResultsListModel.loaded ? 0 : 1
                Behavior on opacity { PropertyAnimation { } }
            }
        }

        onAccepted: {
            var urls = new Array();
            var i;

            for (i=0; i<listView.selectedIndices.length; i++) {
                urls.push(listView.model.get(listView.selectedIndices[i]).url);
            }

            subscribe.subscribe(urls)
        }
    }

}

