
import Qt 4.7

import com.nokia.meego 1.0

import 'config.js' as Config

Item {
    id: episodeList
    property string currentFilterText
    property string mainState

    onMainStateChanged: {
        // Don't remember contentY when leaving episode list
        listView.lastContentY = 0;
    }

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

    onModelChanged: {
        filterDialog.resetSelection();
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

        onContentHeightChanged: {
            if (count > 0 && openedIndex == count - 1 && !flicking && !moving) {
                /* Scroll the "opening" item into view at the bottom */
                listView.positionViewAtEnd();
            }
        }

        property real lastContentY: 0

        onContentYChanged: {
            // Keep Y scroll position when deleting episodes (bug 1660)
            if (contentY === 0) {
                if (lastContentY > 0) {
                    contentY = lastContentY;
                }
            } else {
                if (episodeList.mainState === 'episodes') {
                    // Only store scroll position when the episode list is
                    // shown (avoids overwriting it in onMainStateChanged)
                    lastContentY = contentY;
                }
            }
        }

        anchors.fill: parent
        property int openedIndex: -1
        visible: count > 0

        delegate: Item {
            id: listItem

            height: listItem.opened?(Config.listItemHeight + Config.smallSpacing * 3 + Config.headerHeight):(Config.listItemHeight)
            property bool opened: (index == listView.openedIndex)

            Behavior on height { PropertyAnimation { duration: Config.fastTransition } }

            EpisodeItem {
                id: episodeItem

                y: listItem.opened?Config.smallSpacing:0
                width: listView.width

                onSelected: {
                    if (listView.openedIndex == index) {
                        listView.openedIndex = -1
                        episodeActions.episode = null
                    } else {
                        listView.openedIndex = index
                        episodeActions.episode = modelData
                    }
                }
                onContextMenu: episodeList.episodeContextMenu(item)

                Behavior on y { PropertyAnimation { duration: Config.fastTransition } }
            }
        }
    }

    ScrollDecorator {
        flickableItem: listView
    }

    EpisodeActions {
        id: episodeActions
        Behavior on opacity { PropertyAnimation { duration: Config.fastTransition } }
        property alias modelData: episodeActions.episode
        opacity: listView.openedIndex !== -1

        anchors {
            top: parent.top
            topMargin: {
                if (listView.openedIndex !== -1) {
                    listView.openedIndex * Config.listItemHeight + Config.listItemHeight + Config.smallSpacing * 2 - listView.contentY
                } else {
                    -episodeActions.height
                }
            }
        }

        width: parent.width
    }

    SelectionDialog {
        id: filterDialog
        titleText: _('Show episodes')

        function resetSelection() {
            selectedIndex = episodeList.model.getFilter();
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
        }
    }
}

