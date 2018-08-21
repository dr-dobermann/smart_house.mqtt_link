"""
    uPython gardening pump controller.

    Written for ESP8266

    Uses mqtt server

    (c) Dr. Dobermann, 2018.
"""

import mqtt_link

import mqtt_cont_cfg as cfg
            
        

def main():
    
    c = mqtt_link.init_controller(cfg.MQTT_CLI_NAME, cfg.mqtt_links)
    if c == None:
        print("Fatal error couldn't continue. Terminating")
        return
    
    while mqtt_link.run():
        pass

    mqtt_link.close_controller()
        


if __name__ == "__main__":
    main()