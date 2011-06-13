
import Qt 4.7

import 'config.js' as Config

Item {
    id: subscribe

    property string defaultUrl: 'http://gpodder.net/toplist.opml'

    signal subscribe(variant url)

    function show() {
        searchInput.text = ''
        opmlListModel.source = ''
        searchInput.forceActiveFocus()
    }

    onVisibleChanged: {
        if (!visible) {
            searchInput.closeVirtualKeyboard()
        }
    }

    Item {
        id: topBar
        height: 70

        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
        }

        Text {
            id: searchLabel
            text: 'Search for:'
            color: 'white'
            font.pixelSize: 20
            anchors {
                leftMargin: Config.smallSpacing
                left: parent.left
                verticalCenter: parent.verticalCenter
            }
        }

        InputField {
            id: searchInput

            anchors {
                leftMargin: Config.smallSpacing
                left: searchLabel.right
                right: searchButton.left
                verticalCenter: parent.verticalCenter
            }
        }

        SimpleButton {
            id: searchButton
            //text: 'Search'
            image: 'artwork/search.png'

            onClicked: opmlListModel.searchFor(searchInput.text)

            width: parent.height
            height: parent.height

            anchors {
                top: parent.top
                right: addButton.left
            }
        }

        SimpleButton {
            id: addButton
            //text: 'Add'
            image: 'artwork/subscriptions.png'

            onClicked: subscribe.subscribe(searchInput.text)

            width: parent.height
            height: parent.height

            anchors {
                top: parent.top
                right: parent.right
            }
        }
    }

    ListView {
        id: listView
        clip: true

        opacity: (opmlListModel.status == XmlListModel.Ready)?1:0
        Behavior on opacity { PropertyAnimation { } }

        anchors {
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            top: topBar.bottom
        }

        model: OpmlListModel {
            id: opmlListModel

            function searchFor(query) {
                console.log('Searching for: ' + query)
                source = 'http://gpodder.net/search.opml?q=' + query
                console.log('new source:' + source)
            }
        }

        delegate: SelectableItem {
            property string modelData: url

            height: Config.listItemHeight
            width: listView.width

            Column {
                anchors {
                    leftMargin: Config.largeSpacing
                    left: parent.left
                    right: parent.right
                    verticalCenter: parent.verticalCenter
                }

                Text {
                    text: title
                    anchors.leftMargin: Config.largeSpacing
                    color: 'white'
                    font.pixelSize: 25
                }

                Text {
                    text: url
                    anchors.leftMargin: Config.largeSpacing
                    color: '#aaa'
                    font.pixelSize: 15
                }
            }

            onSelected: subscribe.subscribe(item)
        }
    }

    Rectangle {
        anchors.centerIn: parent

        width: 100
        height: 50

        color: 'black'
        opacity: (opmlListModel.status == XmlListModel.Loading)?1:0

        Behavior on opacity { PropertyAnimation { } }

        Text {
            anchors.centerIn: parent
            text: 'Loading.'
            color: 'white'
            font.pixelSize: 30
        }
    }

    Item {
        id: directoryButtons
        visible: opmlListModel.source == ''

        anchors.fill: parent
        anchors.bottomMargin: Config.listItemHeight

        Row {
            visible: parent.height > 200
            anchors.centerIn: parent
            spacing: Config.largeSpacing * 3

            Image {
                source: 'artwork/directory-toplist.png'

                SelectableItem {
                    property string modelData: 'http://gpodder.org/toplist.opml'
                    anchors.fill: parent
                    onSelected: opmlListModel.source = item
                }

                Text {
                    anchors.top: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    font.pixelSize: 30
                    color: 'white'
                    text: 'Toplist'
                }
            }

            Image {
                source: 'artwork/directory-examples.png'

                SelectableItem {
                    property string modelData: 'http://gpodder.org/directory.opml'
                    anchors.fill: parent
                    onSelected: opmlListModel.source = item
                }

                Text {
                    anchors.top: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    font.pixelSize: 30
                    color: 'white'
                    text: 'Examples'
                }
            }
        }
    }

    Text {
        visible: directoryButtons.visible
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: Config.largeSpacing
        font.pixelSize: 20
        color: 'white'
        text: '<em>powered by gpodder.net</em>'
    }
}

