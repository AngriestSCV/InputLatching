import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "." 1.0

Item {
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        // ── Device card ───────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: deviceCardCol.implicitHeight + 20
            color: Theme.clrSurface; radius: 10
            border.color: Theme.clrBorder; border.width: 1

            ColumnLayout {
                id: deviceCardCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                spacing: 8

                SectionLabel { text: "INPUT DEVICE" }

                RowLayout {
                    spacing: 6
                    ComboBox {
                        id: deviceCombo
                        model: bridge.deviceModel
                        Layout.fillWidth: true
                    }
                    AppButton {
                        text: "↻  Refresh"
                        implicitWidth: 90
                        tint: Qt.rgba(Theme.clrAccent.r, Theme.clrAccent.g, Theme.clrAccent.b, 0.55)
                        onClicked: bridge.refreshDevices()
                    }
                }

                RowLayout {
                    spacing: 6
                    AppButton {
                        text: "＋  Add Device"
                        Layout.fillWidth: true
                        onClicked: bridge.addDevice(deviceCombo.currentText)
                    }
                    AppButton {
                        text: "✕  Clear"
                        tint: Theme.clrRed
                        implicitWidth: 80
                        onClicked: bridge.clearDevices()
                    }
                }
            }
        }

        // ── Transport controls ────────────────────────────────────────────────
        RowLayout {
            spacing: 8
            Layout.fillWidth: true
            AppButton { text: "▶  Start";       tint: Theme.clrGreen;  Layout.fillWidth: true; onClicked: bridge.start() }
            AppButton { text: "■  Stop";        tint: Theme.clrRed;    Layout.fillWidth: true; onClicked: bridge.stop() }
            AppButton { text: "◎  Set Trigger"; tint: Theme.clrOrange; Layout.fillWidth: true; onClicked: bridge.beginSetTrigger() }
        }

        // ── State card ────────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: stateCol.implicitHeight + 20
            color: Theme.clrSurface; radius: 10
            border.color: Theme.clrBorder; border.width: 1

            ColumnLayout {
                id: stateCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                spacing: 8

                SectionLabel { text: "STATUS" }
                RowLayout {
                    spacing: 8
                    StatusPill { active: bridge.running; label: bridge.running ? "Running" : "Stopped"; activeColor: Theme.clrGreen }
                    StatusPill { active: bridge.triggerHeld; label: "Trigger Held"; activeColor: Theme.clrOrange }
                }

                RowLayout {
                    spacing: 6
                    Label { text: "Trigger key"; color: Theme.clrDim;  font.pixelSize: 12 }
                    Label { text: bridge.trigger;  color: Theme.clrText; font.pixelSize: 12; font.weight: Font.Medium }
                }

                Divider {}

                SectionLabel { text: "LATCHED" }
                Flow {
                    Layout.fillWidth: true
                    spacing: 5
                    Repeater {
                        model: bridge.latched !== "None" ? bridge.latched.split(", ") : []
                        KeyChip { keyText: modelData; chipColor: Theme.clrAccent }
                    }
                    Label { visible: bridge.latched === "None"; text: "—"; color: Theme.clrDim; font.pixelSize: 14 }
                }

                Divider {}

                SectionLabel { text: "AUTO-CLICKING" }
                Flow {
                    Layout.fillWidth: true
                    spacing: 5
                    Repeater {
                        model: bridge.autoClickKeys
                        KeyChip { keyText: modelData; chipColor: Theme.clrOrange }
                    }
                    Label { visible: bridge.autoClickKeys.length === 0; text: "—"; color: Theme.clrDim; font.pixelSize: 14 }
                }

                Divider {}

                SectionLabel { text: "DEVICES" }
                Repeater {
                    model: bridge.loadedDevices
                    RowLayout {
                        spacing: 6
                        Layout.fillWidth: true
                        Label {
                            text: modelData
                            color: Theme.clrText
                            font.pixelSize: 12
                            Layout.fillWidth: true
                            elide: Text.ElideMiddle
                        }
                        AppButton {
                            text: "✕"
                            tint: Theme.clrRed
                            implicitWidth: 28
                            implicitHeight: 22
                            onClicked: bridge.removeDevice(modelData)
                        }
                    }
                }
                Label { visible: bridge.loadedDevices.length === 0; text: "—"; color: Theme.clrDim; font.pixelSize: 14 }
            }
        }

        // ── Log card ──────────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#111218"; radius: 10
            border.color: Theme.clrBorder; border.width: 1
            clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6

                RowLayout {
                    SectionLabel { text: "LOG"; Layout.fillWidth: true }
                    AppButton {
                        text: "Clear"
                        implicitWidth: 58
                        implicitHeight: 24
                        tint: Theme.clrBorder
                        onClicked: logArea.clear()
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Flickable {
                        id: logFlick
                        anchors { fill: parent; rightMargin: 10 }
                        contentWidth: width
                        contentHeight: logArea.implicitHeight
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds

                        TextArea {
                            id: logArea
                            width: logFlick.width
                            readOnly: true
                            wrapMode: Text.Wrap
                            color: "#6e8faa"
                            font.family: "monospace"
                            font.pixelSize: 11
                            background: null
                            leftPadding: 0
                        }

                        onContentHeightChanged:
                            contentY = Math.max(0, contentHeight - height)
                    }

                    Rectangle {
                        anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
                        width: 5; radius: 3
                        color: Qt.rgba(Theme.clrDim.r, Theme.clrDim.g, Theme.clrDim.b, 0.12)
                        visible: logFlick.contentHeight > logFlick.height

                        Rectangle {
                            property real ratio:  logFlick.height / Math.max(logFlick.contentHeight, 1)
                            property real thumbH: Math.max(24, ratio * parent.height)
                            property real travel: logFlick.contentHeight - logFlick.height
                            x: 0; width: parent.width; height: thumbH; radius: 3
                            y: travel > 0 ? (logFlick.contentY / travel) * (parent.height - thumbH) : 0
                            color: Qt.rgba(Theme.clrDim.r, Theme.clrDim.g, Theme.clrDim.b, 0.7)
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: bridge
        function onLogAppended(message) { logArea.append(message) }
    }
}
