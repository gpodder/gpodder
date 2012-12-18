
import QtQuick 1.1

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

    function resetFilterDialog() {
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
        cacheBuffer: 10000

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

        delegate: EpisodeItem {
            id: episodeItem
            property variant modelData: episode
            property bool playing: (episode === mediaPlayer.episode) && mediaPlayer.playing

            inSelection: (index === listView.openedIndex)
            opacity: {
                if ((listView.openedIndex === -1) || inSelection) {
                    1
                } else {
                    .3
                }
            }

            height: Config.listItemHeight
            width: listView.width

            onSelected: {
                if (listView.openedIndex !== -1) {
                    listView.openedIndex = -1
                } else {
                    listView.openedIndex = index
                }
            }

            onContextMenu: episodeList.episodeContextMenu(episode)
        }
    }

    EpisodeActions {
        id: episodeActions
        opacity: listView.openedIndex !== -1

        episode: episodeListModel.get(listView.openedIndex)
        playing: {
            if (episode !== undefined) {
                (episode.episode === mediaPlayer.episode) && mediaPlayer.playing
            } else {
                false
            }
        }

        property alias modelData: episodeActions.episode

        anchors {
            top: parent.top
            topMargin: {
                if (listView.openedIndex !== -1) {
                    listView.openedIndex * Config.listItemHeight + Config.listItemHeight - listView.contentY
                } else {
                    -episodeActions.height
                }
            }
            left: parent.left
            right: parent.right
        }
    }

    ScrollDecorator {
        flickableItem: listView
    }

    SelectionDialog {
        id: filterDialog
        titleText: _('Show episodes')

        function resetSelection() {
            if (main.episodeModel !== undefined) {
                selectedIndex = main.episodeModel.getFilter();
                accepted();
            }
        }

        onAccepted: {
            if (main.episodeModel !== undefined) {
                episodeList.currentFilterText = model.get(selectedIndex).name;
                episodeModel.setFilter(selectedIndex);
            }
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

