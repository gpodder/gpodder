
import Qt 4.7

import com.nokia.meego 1.0

import 'config.js' as Config

Item {
    id: subscribe

    signal subscribe(variant url)

    function show() {
        searchInput.text = ''
        searchResultsListModel.source = ''
        searchInput.forceActiveFocus()
        topBar.opened = true
    }

    function search() {
        searchResultsListModel.searchFor(searchInput.text)
    }

    onVisibleChanged: {
        if (!visible) {
            searchInput.closeVirtualKeyboard()
        }
    }

    Item {
        id: topBar
        property bool opened: true
        clip: true

        height: opened?70:0

        Behavior on height { PropertyAnimation { duration: Config.slowTransition } }

        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
        }

        Label {
            id: searchLabel
            text: _('Search for:')
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
            placeholderText: _('Search term or URL')

            anchors {
                leftMargin: Config.smallSpacing
                left: searchLabel.right
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
        id: listView
        clip: true

        opacity: (searchResultsListModel.status == XmlListModel.Ready)?1:0
        Behavior on opacity { PropertyAnimation { } }

        anchors {
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            top: topBar.bottom
        }

        model: SearchResultsListModel {
            id: searchResultsListModel

            function searchFor(query) {
                console.log('Searching for: ' + query)
                source = 'http://gpodder.net/search.xml?q=' + query
                console.log('new source:' + source)
            }
        }

        delegate: SelectableItem {
            property string modelData: url

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
                clip: true

                anchors {
                    leftMargin: Config.largeSpacing
                    rightMargin: Config.largeSpacing
                    left: coverArt.right
                    right: subscriberCount.left
                    verticalCenter: parent.verticalCenter
                }

                Label {
                    text: title
                    anchors.leftMargin: Config.largeSpacing
                    color: 'white'
                    font.pixelSize: 25
                }

                Label {
                    text: url
                    anchors.leftMargin: Config.largeSpacing
                    color: '#aaa'
                    font.pixelSize: 15
                }
            }

            Label {
                id: subscriberCount
                anchors {
                    verticalCenter: parent.verticalCenter
                    leftMargin: Config.largeSpacing
                    right: parent.right
                    rightMargin: Config.largeSpacing
                }
                text: subscribers
                color: 'white'
                font.pixelSize: 30
            }

            onSelected: subscribe.subscribe(item)
        }
    }

    Rectangle {
        anchors.centerIn: parent

        width: 100
        height: 50

        color: 'black'
        opacity: (searchResultsListModel.status == XmlListModel.Loading)?1:0

        Behavior on opacity { PropertyAnimation { } }

        Label {
            anchors.centerIn: parent
            text: _('Loading.')
            color: 'white'
            font.pixelSize: 30
        }
    }

    Item {
        id: directoryButtons
        visible: searchResultsListModel.source == ''

        anchors.fill: parent
        anchors.bottomMargin: Config.listItemHeight

        Row {
            visible: parent.height > 200
            anchors.centerIn: parent
            spacing: Config.largeSpacing * 3

            Image {
                source: 'artwork/directory-toplist.png'

                SelectableItem {
                    property string modelData: 'http://gpodder.net/toplist.xml'
                    anchors.fill: parent
                    onSelected: {
                        searchResultsListModel.source = item
                        topBar.opened = false
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
                    property string modelData: 'http://gpodder.net/gpodder-examples.xml'
                    anchors.fill: parent
                    onSelected: {
                        searchResultsListModel.source = item
                        topBar.opened = false
                    }
                }

                Label {
                    anchors.top: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    font.pixelSize: 30
                    color: 'white'
                    text: _('Examples')
                }
            }
        }
    }

    ScrollDecorator {
        flickableItem: listView
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
}

