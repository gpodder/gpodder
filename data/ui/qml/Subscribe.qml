
import Qt 4.7

import 'config.js' as Config

Item {
    id: subscribe

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
        clip: true

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

            height: 50
            width: parent.width

            Text {
                text: title
                anchors.fill: parent
                verticalAlignment: Text.AlignVCenter
                color: 'white'
                font.pixelSize: 25
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
            text: 'loading...'
            color: 'white'
            font.pixelSize: 14
        }
    }

}

