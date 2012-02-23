
import Qt 4.7

import com.nokia.meego 1.0

import 'config.js' as Config

Item {
    id: episodeList
    property string currentFilterText

    property alias model: listView.model
    property alias moving: listView.moving
    property alias count: listView.count

    signal episodeContextMenu(variant episode)

    function showFilterDialog() {
        filterDialog.open();
    }

    function resetSelection() {
        listView.openedIndex = -1
    }

    Text {
        anchors.centerIn: parent
        color: 'white'
        font.pixelSize: 30
        horizontalAlignment: Text.AlignHCenter
        text: '<big>' + _('No episodes') + '</big>' + '<br><small>' + _('Touch to change filter') + '</small>'
        visible: !listView.visible

        MouseArea {
            anchors.fill: parent
            onClicked: episodeList.showFilterDialog()
        }
    }

    ListView {
        id: listView
        anchors.fill: parent
        property int openedIndex: -1
        visible: count > 0

        delegate: Item {
            id: listItem

            height: listItem.opened?(Config.listItemHeight + Config.smallSpacing * 3 + Config.headerHeight):(Config.listItemHeight)
            width: parent.width
            property bool opened: (index == listView.openedIndex)

            Rectangle {
                color: '#aa000000'
                anchors {
                    fill: parent
                    topMargin: 3
                    bottomMargin: 3
                }
                visible: listItem.opened
            }

            Loader {
                id: loader
                clip: true
                source: listItem.opened?'EpisodeActions.qml':''

                Behavior on opacity { PropertyAnimation { } }

                opacity: listItem.opened

                onItemChanged: {
                    if (item) {
                        item.episode = modelData
                    }
                }

                anchors {
                    left: parent.left
                    right: parent.right
                    top: parent.top
                    topMargin: episodeItem.y + episodeItem.height
                    bottom: parent.bottom
                }

                width: parent.width
            }

            Behavior on height { PropertyAnimation { } }

            EpisodeItem {
                id: episodeItem
                y: listItem.opened?Config.smallSpacing:0
                width: parent.width
                onSelected: {
                    if (listView.openedIndex == index) {
                        listView.openedIndex = -1
                    } else {
                        listView.openedIndex = index
                    }
                }
                onContextMenu: episodeList.episodeContextMenu(item)

                Behavior on y { PropertyAnimation { } }
            }
        }

        header: Item { height: titleBar.height }
        footer: Item { height: Config.headerHeight }
    }

    ScrollDecorator {
        flickableItem: listView
    }

    SelectionDialog {
        id: filterDialog
        titleText: _('Show episodes')

        function resetSelection() {
            selectedIndex = 0;
            accepted();
        }

        onAccepted: {
            episodeList.currentFilterText = model.get(selectedIndex).name;
            episodeList.model.setFilter(selectedIndex);
        }

        model: ListModel {}

        Component.onCompleted: {
            var filters = controller.getEpisodeListFilterNames();

            for (var index in filters) {
                model.append({name: filters[index]});
            }

            resetSelection();
        }
    }
}

