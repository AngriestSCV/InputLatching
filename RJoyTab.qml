import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "." 1.0

Item {
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        // ── Server config card ────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: rjoyConfigCol.implicitHeight + 20
            color: Theme.clrSurface; radius: 10
            border.color: Theme.clrBorder; border.width: 1

            ColumnLayout {
                id: rjoyConfigCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                spacing: 8

                SectionLabel { text: "SERVER CONFIGURATION" }

                RowLayout {
                    spacing: 6
                    Label { text: "Host"; color: Theme.clrDim; font.pixelSize: 12; Layout.preferredWidth: 40 }
                    TextField {
                        id: rjoyHost
                        text: "0.0.0.0"
                        Layout.fillWidth: true
                        color: Theme.clrText
                        font.pixelSize: 12
                        background: Rectangle {
                            color: palette.base
                            border.color: rjoyHost.activeFocus ? Theme.clrAccent : Theme.clrBorder
                            border.width: 1; radius: 6
                        }
                        leftPadding: 8; rightPadding: 8
                    }
                }

                RowLayout {
                    spacing: 6
                    Label { text: "Port"; color: Theme.clrDim; font.pixelSize: 12; Layout.preferredWidth: 40 }
                    TextField {
                        id: rjoyPort
                        text: "8765"
                        Layout.fillWidth: true
                        color: Theme.clrText
                        font.pixelSize: 12
                        validator: IntValidator { bottom: 1; top: 65535 }
                        background: Rectangle {
                            color: palette.base
                            border.color: rjoyPort.activeFocus ? Theme.clrAccent : Theme.clrBorder
                            border.width: 1; radius: 6
                        }
                        leftPadding: 8; rightPadding: 8
                    }
                }
            }
        }

        // ── Transport controls ────────────────────────────────────────────────
        RowLayout {
            spacing: 8
            Layout.fillWidth: true
            AppButton { text: "▶  Start Server"; tint: Theme.clrGreen; Layout.fillWidth: true }
            AppButton { text: "■  Stop Server";  tint: Theme.clrRed;   Layout.fillWidth: true }
        }

        // ── Status card ───────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: rjoyStatusCol.implicitHeight + 20
            color: Theme.clrSurface; radius: 10
            border.color: Theme.clrBorder; border.width: 1

            ColumnLayout {
                id: rjoyStatusCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                spacing: 8

                SectionLabel { text: "STATUS" }

                RowLayout {
                    spacing: 8
                    StatusPill { active: false; label: active ? "Running" : "Stopped"; activeColor: Theme.clrGreen }
                    StatusPill { active: false; label: "0 clients"; activeColor: Theme.clrAccent }
                }

                Divider {}

                RowLayout {
                    spacing: 6
                    Label { text: "URL";      color: Theme.clrDim; font.pixelSize: 12; Layout.preferredWidth: 60 }
                    Label { text: "ws://" + rjoyHost.text + ":" + rjoyPort.text; color: Theme.clrText; font.pixelSize: 12; font.family: "monospace" }
                }
                RowLayout {
                    spacing: 6
                    Label { text: "Uptime";   color: Theme.clrDim; font.pixelSize: 12; Layout.preferredWidth: 60 }
                    Label { text: "—"; color: Theme.clrText; font.pixelSize: 12 }
                }
                RowLayout {
                    spacing: 6
                    Label { text: "Sent";     color: Theme.clrDim; font.pixelSize: 12; Layout.preferredWidth: 60 }
                    Label { text: "—"; color: Theme.clrText; font.pixelSize: 12 }
                }
                RowLayout {
                    spacing: 6
                    Label { text: "Received"; color: Theme.clrDim; font.pixelSize: 12; Layout.preferredWidth: 60 }
                    Label { text: "—"; color: Theme.clrText; font.pixelSize: 12 }
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
