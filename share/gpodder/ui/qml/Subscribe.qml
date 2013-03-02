
import QtQuick 1.1

import com.nokia.meego 1.0
import org.gpodder.qmlui 1.0

import 'config.js' as Config

Item {
    id: subscribe

    signal subscribe(variant urls)

    function show() {
        searchInput.text = ''
        searchResultsListModel.source = ''
        resultsSheet.reject();
    }

    function search() {
        searchResultsListModel.searchFor(searchInput.text);
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

    Item {
        id: directoryButtons

        anchors.fill: parent
        anchors.bottomMargin: Config.listItemHeight

        Row {
            visible: parent.height > 200
            anchors.centerIn: parent
            spacing: Config.largeSpacing * 3

            Image {
                source: 'artwork/directory-toplist.png'

                SelectableItem {
                    property string modelData: 'http://gpodder.org/directory/toplist.xml'
                    anchors.fill: parent
                    onSelected: {
                        searchResultsListModel.source = item;
                        resultsSheet.open();
                    }
                }

                Label {
                    anchors.top: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    font.pixelSize: 30
                    color: 'white'
                    text: _('Toplist')
                }
            }

            Image {
                source: 'artwork/directory-examples.png'

                SelectableItem {
                    property string modelData: controller.myGpoEnabled?('http://' + controller.myGpoUsername + ':' + controller.myGpoPassword + '@gpodder.net/subscriptions/' + controller.myGpoUsername + '.xml'):('http://gpodder.org/directory/examples.xml')
                    anchors.fill: parent
                    onSelected: {
                        searchResultsListModel.source = item;
                        resultsSheet.open();
                    }
                }

                Label {
                    anchors.top: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    font.pixelSize: 30
                    color: 'white'
                    text: controller.myGpoEnabled?_('My gpodder.net'):_('Examples')
                }
            }
        }
    }

    Label {
        visible: directoryButtons.visible
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: Config.largeSpacing
        font.pixelSize: 20
        color: 'white'
        text: '<em>' + _('powered by gpodder.net') + '</em>'
    }

    Sheet {
        id: resultsSheet

        anchors.fill: parent
        anchors.topMargin: -50

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

                opacity: (searchResultsListModel.status == XmlListModel.Ready)?1:0
                Behavior on opacity { PropertyAnimation { } }

                anchors.fill: parent

                model: SearchResultsListModel {
                    id: searchResultsListModel

                    function searchFor(query) {
                        console.log('Searching for: ' + query)
                        source = 'http://gpodder.net/search.xml?q=' + query
                        console.log('new source:' + source)
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
                            source: logo
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
                platformStyle: BusyIndicatorStyle { size: "large" }

                opacity: (searchResultsListModel.status == XmlListModel.Loading)?1:0
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

