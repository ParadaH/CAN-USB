#include <SPI.h>
#include <mcp_can.h>

#define CAN0_INT 2
MCP_CAN CAN0(10);

void setup() {
    Serial.begin(115200);
    
    while (CAN0.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ) != CAN_OK) {
        Serial.println("Error initializing CAN Bus. Retrying...");
        delay(1000);
    }
    Serial.println("CAN Bus initialized!");

    CAN0.setMode(MCP_NORMAL);
    Serial.println("Enter CAN message in format: 0xID DATA1 DATA2 ... DATA8");
}

void loop() {
    if (!digitalRead(CAN0_INT)) {
        unsigned long id;
        unsigned char len = 0;
        unsigned char buf[8];

        if (CAN0.readMsgBuf(&id, &len, buf) == CAN_OK) {
            Serial.print("Received: ID 0x"); Serial.print(id, HEX);
            Serial.print(" Data: ");
            for (int i = 0; i < len; i++) {
                Serial.print(buf[i], HEX);
                Serial.print(" ");
            }
            Serial.println();
        }
    }
    
    if (Serial.available()) {
        String input = Serial.readStringUntil('\n');
        input.trim();
        
        if (input.length() == 0) return;
        
        char *token;
        char buffer[50];
        input.toCharArray(buffer, 50);
        
        token = strtok(buffer, " ");
        if (token == NULL || strncmp(token, "0x", 2) != 0) {
            Serial.println("Invalid format. Use: 0xID DATA1 DATA2 ...");
            return;
        }
        
        unsigned long id = strtoul(token, NULL, 16);
        unsigned char data[8];
        int dataLen = 0;
        
        while ((token = strtok(NULL, " ")) != NULL && dataLen < 8) {
            data[dataLen++] = strtoul(token, NULL, 16);
        }
        
        if (CAN0.sendMsgBuf(id, 0, dataLen, data) == CAN_OK) {
            Serial.print("Sent: ID: 0x"); Serial.print(id, HEX);
            Serial.print(" Data: ");
            for (int i = 0; i < dataLen; i++) {
                Serial.print(data[i], HEX);
                Serial.print(" ");
            }
            Serial.println();
        } else {
            Serial.println("Error sending message.");
        }
    }
}
