#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <PMserial.h> // Modified PMSerial Library

#define SENSOR_NAME "parSensor"
#define TOPIC "sensors/pmsensor/count"
#define MSG_BUFFER_SIZE (255)
char msg[MSG_BUFFER_SIZE];

const bool DEBUG = false;
long lastReconnectAttempt = 0;

// WiFi Settings
const char ssid[] = "SSID";
const char pass[] = "SSID_PASSWORD";

// MQTT Settings
const char mqtt_username[] = "MQTT_USER";
const char mqtt_password[] = "MQTT_PASSWORD";
const IPAddress mqtt_server(192, 168, 1, 1);
unsigned int localPort = 1883;

// Function definitions
void callback(char *topic, byte *payload, unsigned int length);
boolean reconnect();

// PIN Defintions
#if !defined(PMS_RX) && !defined(PMS_TX)
const uint8_t PMS_RX = D3, PMS_TX = D4;
#endif

// Global objects
SerialPM pms(PMS5003, PMS_RX, PMS_TX); // PMSx003, RX, TX
LiquidCrystal_I2C lcd(0x27, 16, 2);
WiFiClient espClient;
PubSubClient client(espClient);

void setup()
{
  // LCD Setup
  lcd.init();
  lcd.begin(16,2);
  lcd.print("Connecting...");
  lcd.backlight();

  Serial.begin(115200);
  Serial.println(F("Booted"));

  Serial.println(F("PMS sensor on SWSerial"));
  Serial.print(F("  RX:"));
  Serial.println(PMS_RX);
  Serial.print(F("  TX:"));
  Serial.println(PMS_TX);

  // Connect to LOCAL AP
  WiFi.begin(ssid, pass);
  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  Serial.print("Connected, IP address: ");
  Serial.println(WiFi.localIP());

  pms.init();

  // MQTT Setup
  client.setServer(mqtt_server, localPort);
  client.setCallback(callback);
}

void loop()
{
  if (!client.connected())
  {
    Serial.println("Attempting to Reconnect to MQTT Server");
    long now = millis();
    if (now - lastReconnectAttempt > 5000)
    {
      lastReconnectAttempt = now;
      // Attempt to reconnect
      if (reconnect())
      {
        Serial.println("Client Reconnected!");
        lastReconnectAttempt = 0;
      }
    }
  }
  else
  {
    // Client connected
    if (pms.has_number_concentration())
    {
      pms.read();
      // print formatted results
      Serial.printf("PM1.0 %2d, PM2.5 %2d, PM10 %2d [ug/m3]\n",
                    pms.pm01, pms.pm25, pms.pm10);
      Serial.printf("n0p3: %2d, n0p5: %2d, n1p0: %2d, n2p5: %2d, n5p0: %2d, n10p0: %2d [#/100cm3]\n",
                    pms.n0p3, pms.n0p5, pms.n1p0, pms.n2p5, pms.n5p0, pms.n10p0);

      if (pms)
      {
        // Write to LCD
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.printf("p3: %2d p5: %2d", pms.n0p3, pms.n0p5);
        lcd.setCursor(0, 1);
        lcd.printf("p1: %2d p2: %2d", pms.n1p0, pms.n2p5);

        // Publish Results
        snprintf(msg, MSG_BUFFER_SIZE,
                 "{\"PMS\":{\"P1\":%d,\"P25\":%d,\"P10\":%d,\"B03\":%d,\"B05\":%d,\"B1\":%d,\"B25\":%d,\"B5\":%d,\"B10\":%d}}",
                 pms.pm01, pms.pm25, pms.pm10, pms.n0p3, pms.n0p5, pms.n1p0, pms.n2p5, pms.n5p0, pms.n10p0);
        Serial.print("Publish message: ");
        Serial.println(msg);
        client.publish("sensors/pmsensor/count", msg);
      }
      else
      { // something went wrong
        switch (pms.status)
        {
        case pms.OK: // should never come here
          break;     // included to compile without warnings
        case pms.ERROR_TIMEOUT:
          Serial.println(F(PMS_ERROR_TIMEOUT));
          break;
        case pms.ERROR_MSG_UNKNOWN:
          Serial.println(F(PMS_ERROR_MSG_UNKNOWN));
          break;
        case pms.ERROR_MSG_HEADER:
          Serial.println(F(PMS_ERROR_MSG_HEADER));
          break;
        case pms.ERROR_MSG_BODY:
          Serial.println(F(PMS_ERROR_MSG_BODY));
          break;
        case pms.ERROR_MSG_START:
          Serial.println(F(PMS_ERROR_MSG_START));
          break;
        case pms.ERROR_MSG_LENGTH:
          Serial.println(F(PMS_ERROR_MSG_LENGTH));
          break;
        case pms.ERROR_MSG_CKSUM:
          Serial.println(F(PMS_ERROR_MSG_CKSUM));
          break;
        case pms.ERROR_PMS_TYPE:
          Serial.println(F(PMS_ERROR_PMS_TYPE));
          break;
        }
      }
    }
    client.loop();
  } 
  delay(500);
}

boolean reconnect()
{
  String clientId = "ESP8266Client-";
  clientId += String(random(0xffff), HEX);
  if (client.connect(clientId.c_str(), mqtt_username, mqtt_password))
  {
    // Once connected, publish an announcement...
    //client.publish("topic", "{}");
    // ... and resubscribe
    //client.subscribe("inTopic");
  }
  else
  {
    Serial.print("failed, rc=");
    Serial.print(client.state());
    Serial.println(" try again in 5 seconds");
  }
  return client.connected();
}

void callback(char *topic, byte *payload, unsigned int length)
{
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  for (unsigned int i = 0; i < length; i++)
  {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}
