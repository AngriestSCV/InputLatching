import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "." 1.0

ApplicationWindow {
    id: window
    width: 520
    height: 700
    title: "Latch Input Tool"
    visible: true
    color: "#16171f"

    palette.window:          "#16171f"
    palette.windowText:      "#c9cad8"
    palette.base:            "#21222e"
    palette.alternateBase:   "#292a38"
    palette.button:          "#2e2f40"
    palette.buttonText:      "#c9cad8"
    palette.highlight:       "#7b68ee"
    palette.highlightedText: "#ffffff"
    palette.text:            "#c9cad8"
    palette.mid:             "#3a3b52"
    palette.dark:            "#111218"
    palette.light:           "#3a3b52"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TabBar {
            id: tabBar
            Layout.fillWidth: true
            background: Rectangle { color: Theme.clrSurface; border.color: Theme.clrBorder; border.width: 1 }

            TabButton {
                text: "Latching"
                contentItem: Text {
                    text: parent.text
                    color: tabBar.currentIndex === 0 ? Theme.clrAccent : Theme.clrDim
                    font.pixelSize: 12; font.weight: Font.Medium
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    color: tabBar.currentIndex === 0 ? "#16171f" : Theme.clrSurface
                    border.color: Theme.clrBorder; border.width: 1
                }
            }

            TabButton {
                text: "RJoy"
                contentItem: Text {
                    text: parent.text
                    color: tabBar.currentIndex === 1 ? Theme.clrAccent : Theme.clrDim
                    font.pixelSize: 12; font.weight: Font.Medium
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    color: tabBar.currentIndex === 1 ? "#16171f" : Theme.clrSurface
                    border.color: Theme.clrBorder; border.width: 1
                }
            }
        }

        StackLayout {
            currentIndex: tabBar.currentIndex
            Layout.fillWidth: true
            Layout.fillHeight: true

            LatchingTab {}
            RJoyTab {}
        }
    }
}
