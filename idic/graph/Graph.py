'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Oct 10, 2015

@author: yuki.wu@emc.com
*********************************************************
'''
import time

class CGraph(object):
    def __init__(self):
        self.monorail = None
        self.ssh = None
        self.log = None

    def config(self, monorail, ssh, log, stack):
        self.monorail = monorail
        self.ssh = ssh
        self.log = log
        self.stack = stack

    def fan_get_value_by_telnet(self, node_id, bmc_ip):
        """
        Steps of this test case: 
            1. telnet to the compute node with <telnet bmc_ip 9300>. 
            2. Send "sensor value get 0xc0" and get the response. The result would like below: 
                IPMI_SIM> sensor value get 0xc0
                Fan_SYS0_1 : 3000.000 RPM
            3. Analysis the result in 2 and then return the value of Fan_SYS0_1

        @node_id: compute node id
        @bmc_ip: bmc ip address
        @return: the fan value or -1 if cannot get the fan value.
        """
        str_telnet = "telnet " + bmc_ip + " 9300"
        fan_sys0_1_value_get = "sensor value get 0xc0"
        str_quit = "quit"
        
        # Telnet to the node by <telnet bmc_ip 9300>
        try:
            self.ssh.start_cache()
            ssh_log = self.ssh.send_command_wait_string(str_command= str_telnet + chr(13),
                                                        wait='IPMI_SIM',
                                                        int_time_out=120,
                                                        b_with_buff=False)
            self.log('DEBUG', ssh_log)
        except Exception, e:
            self.log('ERROR', "Node {} with IP {} fail to telnet. Fail Reason: {}".format(node_id, bmc_ip, str(e)))
            return -1

        fan_value_output = ""
        try:
            # Send "sensor value get 0xc0" command and get the result.
            self.ssh.start_cache()
            self.ssh.send_command(fan_sys0_1_value_get + chr(13))
            time.sleep(1)
            fan_value_output = self.ssh.get_cache()
            self.log('DEBUG', fan_value_output)
        except Exception, e:
            self.log('ERROR', "Node {} with IP {} fail to get the FAN value. Fail reason: {}".format(node_id, bmc_ip,str(e)))
        finally:
            # close the telnet 
            self.ssh.start_cache()
            self.ssh.send_command(str_quit + chr(13))
            time.sleep(1)
            self.log('DEBUG', self.ssh.get_cache())

        # Handle the fan_value_output and then get the value of Fan_SYS0_1. 
        if fan_value_output != "":
            try:
                fan_value = ""
                for fan_value_output_in_line in fan_value_output.split("\n"):
                    if fan_value_output_in_line.find("Fan_SYS") != -1:
                        fan_value = fan_value_output_in_line.replace(" ","").split(":")[1]
                        self.log('INFO', "Fan_SYS0_1 Original value: {}".format(fan_value))
                if fan_value !="":
                    return fan_value
                else:
                    return -1
            except Exception, e:
                self.log('ERROR', "Node {} with IP {} fail to get the FAN value. Fail Reason: {}".format(node_id, bmc_ip, str(e)))
                return -1
        else: 
            return -1

    def fan_change_value_by_telnet(self, node_id, bmc_ip, value_to_change):
        """
        change the fan value of Fan_SYS0_1 by <telnet bmc_ip 9300>. 
        Steps of this test case: 
            1. telnet to the compute node with <telnet bmc_ip 9300>. 
            2. Send "sensor value set 0xc0 <value_to_change>".

        @node_id: compute node id
        @bmc_ip: bmc ip address
        @value_to_change: the fan value that you want to change.
        @return: true or false.
        """
        str_telnet = "telnet " + bmc_ip + " 9300"
        fan_sys0_1_value_set = "sensor value set 0xc0 " + str(value_to_change)
        str_quit = "quit"
        
        # Telnet to the node by <telnet bmc_ip 9300> and then change one fan value
        self.ssh.start_cache()
        try:
            telnet_log = self.ssh.send_command_wait_string(str_command= str_telnet + chr(13),
                                                           wait='IPMI_SIM',
                                                           int_time_out=120,
                                                           b_with_buff=False)
            self.log('DEBUG', telnet_log)
        except Exception, e:
            self.log('ERROR', "Node {} with IP {} fail to telnet. Fail Reason: {}".format(node_id, bmc_ip, str(e)))

        # Change the FAN_SYS0 value
        try:
            self.ssh.start_cache()
            self.ssh.send_command(fan_sys0_1_value_set + chr(13))
            time.sleep(1)
            self.log('DEBUG', self.ssh.get_cache())
        except Exception, e:
            self.log('ERROR', "Node {} with IP {} fail to change the FAN value. Fail reason: {}".format(node_id, bmc_ip,str(e)))
        finally:
            # close the telnet 
            self.ssh.start_cache()
            self.ssh.send_command(str_quit + chr(13))
            time.sleep(1)
            self.log('DEBUG', self.ssh.get_cache())

    def fan_get_dic_by_ipmi(self, node_id, bmc_ip, bmc_username, bmc_password, fan_return_dic):
        """
        Get the fan information dic by ipmi command
        Steps of this test case: 
            1. send ipmi command "ipmitool -I lanplus -U admin -P admin -H 172.31.131.130 sdr type fan" to the compute node and get the response like below.
                    Fan_SYS0         | C0h | ok  | 29.1 | 4600 % RPM
                    Fan_SYS1         | C1h | ok  | 29.1 | 2200 % RPM
                    Fan_SYS2         | C2h | ok  | 29.1 | 2600 % RPM
                    Fan_SYS3         | C3h | ok  | 29.1 | 2300 % RPM
                    Fan_SYS4         | C4h | ok  | 29.1 | 3500 % RPM
                    Fan_SYS5         | C5h | ok  | 29.1 | 3100 % RPM
                    Fan_SYS6         | C6h | ok  | 29.1 | 3600 % RPM
                    Fan_SYS7         | C7h | ok  | 29.1 | 3100 % RPM
                    Fan_SSD0         | FCh | ok  | 29.1 | 0 % RPM
                    Fan_SSD1         | FDh | ok  | 29.1 | 0 % RPM

            2. Analysis the result in # 1 and render the response into a dictionary. Currently we only get column 1/3/4/5 information. 

        @node_id: compute node id
        @bmc_ip: bmc ip address
        @fan_return_dic: this value is to record the return dictionary. It will render the dictionary in test case.
        @return: A dic. The format is as below: 
            {
                SystemID: { Fan_SYS_0: {"Health":"XXX","MemberId":"XXX","ReadingRPM":"XXX"},
                            Fan_SYS_0: {"Health":"XXX","MemberId":"XXX","ReadingRPM":"XXX"}}
            }
        """
        all_fan_value_dic = {}
        str_ssh = "ipmitool -I lanplus -U {} -P {} -H {} sdr type fan".format(bmc_username, bmc_password, bmc_ip)

        try:
            self.ssh.start_cache()
            # Use IPMI to get the fan value
            fan = self.ssh.send_command_wait_string(str_command=str_ssh + chr(13),
                                                    wait="$",
                                                    int_time_out=60,
                                                    b_with_buff=False)
            time.sleep(2)
            self.log('DEBUG', self.ssh.get_cache())
        except Exception, e:
            self.log('ERROR', "Node {} IP {}: FAIL to IPMI to the system. Fail Reason {}".format(node_id, bmc_ip, str(e)))

        try:
            # try to construct the dictionary
            for fan_in_line in fan.split("\n"):
                if fan_in_line.find("Fan") != -1:
                    oneFanValues = fan_in_line.replace(" ","").split("|")
                    all_fan_value_dic[oneFanValues[0]] = {"Health": oneFanValues[2], 
                                                          "MemberId": oneFanValues[3], 
                                                          "ReadingRPM": oneFanValues[4].split("%")[0]}
            fan_return_dic[node_id] = all_fan_value_dic
        except Exception, e:
            self.log('ERROR', "Node {} IP {}: Error happens when construct the fan value dictionary. Fail reason: {}".format(node_id, bmc_ip, str(e)))

    def sel_inject_by_telnet_9300(self, node_id, bmc_ip, list_sel):
        """
        Inject an SEL error by telnet. 
        Steps of this test case: 
            1. telnet to the compute node with <telnet bmc_ip 9300>. 
            2. Send "sensor value set 0xc0 <value_to_change>".
        @node_id: compute node id
        @bmc_ip: bmc ip address
        @list_sel: SEL to inject, for each list item, it should be a dict as
        {
            "assertType": "assert"|"deassert", # The type to insert. Default is assert.
            "sensorID": "0x45", # for example, # Sensor ID. 0x45 represents HDD0.
            "eventID": "1", # the event ID. This information comes from "sel get <sensorID>"
        }
        @return: true or false.
        """
        str_telnet = "telnet " + bmc_ip + " 9300"
        str_inject_cmd = "sel set {} {} {}"
        str_shell_prompt = 'IPMI_SIM>'
        str_quit = "quit"

        # start the telnet connect to Hongtao's script to inject SEL
        try:
            # telnet to the node telnet <ip> 9300
            self.ssh.start_cache()
            self.ssh.send_command_wait_string(str_command=str_telnet + chr(13),
                                              int_time_out=10,
                                              wait=str_shell_prompt,
                                              b_with_buff=False)
            self.log('DEBUG', self.ssh.get_cache())
        except Exception, e:
            self.log('ERROR', "Node {} fail to telnet to BMC {}\n{}".format(node_id, bmc_ip, str(e)))
            return

        try:
            for dict_sel in list_sel:

                # inject an SEL error
                str_inject_sel_cmd = str_inject_cmd.\
                    format(dict_sel['sensorID'],
                           dict_sel['eventID'],
                           dict_sel['assertType'])
                self.ssh.start_cache()
                self.ssh.send_command_wait_string(str_command=str_inject_sel_cmd + chr(13),
                                                  int_time_out=2,
                                                  wait=str_shell_prompt,
                                                  b_with_buff=False)
        except Exception, e:
            self.log('ERROR', "Node {} fail to inject SEL on BMC {}\n{}".format(node_id, bmc_ip, str(e)))
        finally:
            # quit the telnet console
            self.ssh.start_cache()
            self.ssh.send_command_wait_string(str_command=str_quit + chr(13),
                                              int_time_out=1,
                                              wait='$',
                                              b_with_buff=False)
            self.log('DEBUG', self.ssh.get_cache())

    def temperature_get_dic_by_ipmi(self, node_id, bmc_ip, bmc_username, bmc_password, temperature_return_dic):
        """
        Get the temperature information dic by ipmi command
        Steps of this test case: 
            1. send ipmi command "ipmitool -I lanplus -U admin -P admin -H 172.31.131.130 sdr type temp" to the compute node and get the response like below.
                    PCH Thermal Trip | BFh | ok  |  7.1 |
                    Temp_Ambient_FP  | EEh | ok  | 64.1 | 29 % degrees C
                    Temp_CPU0        | AAh | ok  | 65.1 | 45 % degrees C
                    Temp_CPU1        | ABh | ok  | 65.2 | 38 % degrees C
                    Temp_DIMM_AB     | ACh | ok  | 66.1 | 33 % degrees C
                    Temp_DIMM_CD     | ADh | ok  | 66.2 | 35 % degrees C
                    Temp_DIMM_EF     | AEh | ok  | 66.3 | 35 % degrees C
                    Temp_DIMM_GH     | AFh | ok  | 66.4 | 35 % degrees C
                    Temp_PCI_Area    | BAh | ok  | 66.11 | 39 % degrees C
                    Temp_Outlet      | 68h | ok  |  7.1 | 32 % degrees C
                    Temp_PCH         | BEh | ok  | 66.14 | 45 % degrees C
                    Temp_PCI_Inlet1  | ECh | ok  | 66.12 | 40 % degrees C
                    Temp_PCI_Inlet2  | EDh | ok  | 66.13 | 34 % degrees C
                    Temp_VR_CPU0     | B1h | ok  | 66.5 | 34 % degrees C
                    Temp_VR_CPU1     | B2h | ok  | 66.6 | 37 % degrees C
                    Temp_VR_DIMM_AB  | B3h | ok  | 66.7 | 32 % degrees C
                    Temp_VR_DIMM_CD  | B4h | ok  | 66.8 | 33 % degrees C
                    Temp_VR_DIMM_EF  | B5h | ok  | 66.9 | 34 % degrees C
                    Temp_VR_DIMM_GH  | B6h | ok  | 66.10 | 34 % degrees C
                    MB Thermal Trip  | B9h | ok  |  7.1 |
                    Temp_SSD0        | FAh | ok  |  7.16 | 0 % degrees C
                    Temp_SSD1        | FBh | ok  |  7.17 | 0 % degrees C

            2. Analysis the result in # 1 and render the response into a dictionary. Currently we only get column 1/3/4/5 information. 

        @node_id: compute node id
        @bmc_ip: bmc ip address
        @temperature_return_dic: this value is to record the return dictionary. It will render the dictionary in test case.
        @return: A dic. The format is as below: 
            {
                SystemID: { Temp_CPU0: {"Health":"XXX","MemberId":"XXX","ReadingCelsius":"XXX"},
                            Temp_CPU1: {"Health":"XXX","MemberId":"XXX","ReadingCelsius":"XXX"}, 
                            ...
                          }
            }
        """
        all_temp_value_dic = {}
        str_ssh = "ipmitool -I lanplus -U {} -P {} -H {} sdr type temp".format(bmc_username,bmc_password,bmc_ip)

        try:
            self.ssh.start_cache()
            # Use IPMI to get the temperature value
            temp = self.ssh.send_command_wait_string(str_command=str_ssh + chr(13),
                                                     wait="$",
                                                     int_time_out=60,
                                                     b_with_buff=False)
            time.sleep(2)
            self.log('DEBUG', self.ssh.get_cache())
        except Exception, e:
            self.log('ERROR', "Node {} IP {}: FAIL to IPMI to the system. Fail Reason {}".format(node_id, bmc_ip, str(e)))

        try:
            # try to construct the dictionary
            for temp_in_line in temp.split("\n"):
                if temp_in_line.find("Temp_") != -1:
                    oneTempValues = temp_in_line.replace(" ","").split("|")
                    all_temp_value_dic[oneTempValues[0]] = {"Health": oneTempValues[2], 
                                                            "MemberId": oneTempValues[3], 
                                                            "ReadingCelsius": oneTempValues[4].split("%")[0]}
            temperature_return_dic[node_id] = all_temp_value_dic
        except Exception, e:
            self.log('ERROR', "Node {} IP {}: Error happens when construct the temperature value dictionary. Fail reason: {}".format(node_id, bmc_ip, str(e)))

    def temperature_get_value_by_telnet(self, node_id, bmc_ip, sensor_ID="0xaa"):
        """
        Steps of this test case: 
            1. telnet to the compute node with <telnet bmc_ip 9300>. 
            2. Send "sensor value get <sensor ID>" and get the response. The result would like below: 
                IPMI_SIM> sensor value get 0xaa
                Temp_CPU0 : 45.000 degrees C
            3. Analysis the result in 2 and then return the value of Temperature sensor.

        @node_id: compute node id
        @bmc_ip: bmc ip address
        @sensor_ID: the sensor that you want to change value.
        @return: the temperature value or raise an exception when cannot get the temperature.
        """
        str_telnet = "telnet " + bmc_ip + " 9300"
        temp_value_get = "sensor value get {}".format(sensor_ID)
        str_quit = "quit"
        
        # Telnet to the node by <telnet bmc_ip 9300>
        try:
            self.ssh.start_cache()
            ssh_log = self.ssh.send_command_wait_string(str_command= str_telnet + chr(13),
                                                        wait='IPMI_SIM',
                                                        int_time_out=120,
                                                        b_with_buff=False)
            self.log('DEBUG', ssh_log)
        except Exception, e:
            self.log('ERROR', "Node {} with IP {} fail to telnet. Fail Reason: {}".format(node_id, bmc_ip, str(e)))

        temperature_value_output = ""
        try:
            # Send "sensor value get <sensor ID>" command and get the result.
            self.ssh.start_cache()
            self.ssh.send_command(temp_value_get + chr(13))
            time.sleep(1)
            temperature_value_output = self.ssh.get_cache()
            self.log('DEBUG', temperature_value_output)
        except Exception, e:
            self.log('ERROR', "Node {} with IP {} fail to get the Temperature value. Fail reason: {}".format(node_id, bmc_ip,str(e)))
        finally:
            # close the telnet 
            self.ssh.start_cache()
            self.ssh.send_command(str_quit + chr(13))
            time.sleep(1)
            self.log('DEBUG', self.ssh.get_cache())

        # Handle the temperature_value_output and then get the value of <sensor_ID>. 
        if temperature_value_output == "":
            raise ValueError("Node {} with IP {} fail to get the Temperature value.".format(node_id, bmc_ip))

        temp_value = ""
        for temperature_value_output_in_line in temperature_value_output.split("\n"):
            if temperature_value_output_in_line.find("Temp_") != -1:
                temp_value = temperature_value_output_in_line.replace(" ","").split(":")[1]
                self.log('INFO', "The Original Temperature value for Sensor {}: {}".format(sensor_ID, temp_value))
        if temp_value == "":
            raise ValueError("Node {} with IP {} fail to get the Temperature value.".format(node_id, bmc_ip))
            return
        return temp_value

    def temperature_change_value_by_telnet(self, node_id, bmc_ip, value_to_change="45", sensor_ID="0xaa"):
        """
        change the temperature value of <sensor_ID> by <telnet bmc_ip 9300>. 
        Steps of this test case: 
            1. telnet to the compute node with <telnet bmc_ip 9300>. 
            2. Send "sensor value set <sensor_ID> <value_to_change>".

        @node_id: compute node id
        @bmc_ip: bmc ip address
        @value_to_change: the temperature value that you want to change.
        @sensor_ID: the sensor that you want to change value.
        """
        str_telnet = "telnet " + bmc_ip + " 9300"
        temp_value_set = "sensor value set {} {}".format(sensor_ID, value_to_change)
        str_quit = "quit"
        
        # Telnet to the node by <telnet bmc_ip 9300> and then change one temperature value
        self.ssh.start_cache()
        try:
            telnet_log = self.ssh.send_command_wait_string(str_command= str_telnet + chr(13),
                                                           wait='IPMI_SIM',
                                                           int_time_out=120,
                                                           b_with_buff=False)
            self.log('DEBUG', telnet_log)
        except Exception, e:
            self.log('ERROR', "Node {} with IP {} fail to telnet. Fail Reason: {}".format(node_id, bmc_ip, str(e)))

        # Change the <sensor_ID> value
        try:
            self.ssh.start_cache()
            self.ssh.send_command(temp_value_set + chr(13))
            time.sleep(1)
            self.log('DEBUG', self.ssh.get_cache())
        except Exception, e:
            self.log('ERROR', "Node {} with IP {} fail to change the FAN value. Fail reason: {}".format(node_id, bmc_ip,str(e)))
        finally:
            # close the telnet 
            self.ssh.start_cache()
            self.ssh.send_command(str_quit + chr(13))
            time.sleep(1)
            self.log('DEBUG', self.ssh.get_cache())

    def voltage_get_dic_by_ipmi(self, node_id, bmc_ip, bmc_username, bmc_password, voltage_return_dic):
        """
        Get the voltage information dic by ipmi command
        Steps of this test case: 
            1. send ipmi command "ipmitool -I lanplus -U admin -P admin -H 172.31.131.130 sdr type voltage" to the compute node and get the response like below.
                    Volt_VR_CPU0     | DAh | ok  |  7.1 | 1.80 % Volts
                    Volt_VR_CPU1     | DBh | ok  |  7.1 | 1.81 % Volts
                    Volt_P5V         | D1h | ok  |  7.1 | 4.94 % Volts
                    Volt_P5V_AUX     | D6h | ok  |  7.1 | 4.91 % Volts
                    Volt_P3V3        | D0h | ok  |  7.1 | 3.32 % Volts
                    Volt_P1V05       | D3h | ok  |  7.1 | 1.05 % Volts
                    Volt_P1V8_AUX    | D4h | ok  |  7.1 | 1.80 % Volts
                    Volt_P12V        | D2h | ok  |  7.1 | 12.24 % Volts
                    Volt_P3V3_AUX    | D5h | ok  |  7.1 | 3.32 % Volts
                    Volt_VR_DIMM_AB  | DCh | ok  |  7.1 | 1.22 % Volts
                    Volt_VR_DIMM_EF  | DEh | ok  |  7.1 | 1.22 % Volts
                    Volt_VR_DIMM_GH  | DFh | ok  |  7.1 | 1.22 % Volts
                    Volt_VR_DIMM_CD  | DDh | ok  |  7.1 | 1.22 % Volts
                    Volt_P3V_BAT     | D7h | ok  |  7.1 | 3.22 % Volts

            2. Analysis the result in # 1 and render the response into a dictionary. Currently we only get column 1/3/4/5 information. 

        @node_id: compute node id
        @bmc_ip: bmc ip address
        @voltage_return_dic: this value is to record the return dictionary. It will render the dictionary in test case.
        @return: A dic. The format is as below: 
            {
                SystemID: { Volt_VR_CPU0: {"Health":"XXX","MemberId":"XXX","ReadingVolts":"XXX"},
                            Volt_VR_CPU1: {"Health":"XXX","MemberId":"XXX","ReadingVolts":"XXX"}, 
                            ...
                          }
            }
        """
        all_voltage_value_dic = {}
        str_ssh = "ipmitool -I lanplus -U {} -P {} -H {} sdr type voltage".format(bmc_username,bmc_password,bmc_ip)

        try:
            self.ssh.start_cache()
            # Use IPMI to get the voltage value
            voltage = self.ssh.send_command_wait_string(str_command=str_ssh + chr(13),
                                                        wait="$",
                                                        int_time_out=60,
                                                        b_with_buff=False)
            time.sleep(2)
            self.log('DEBUG', self.ssh.get_cache())
        except Exception, e:
            self.log('ERROR', "Node {} IP {}: FAIL to IPMI to the system. Fail Reason {}".format(node_id, bmc_ip, str(e)))

        try:
            # try to construct the dictionary
            for voltage_in_line in voltage.split("\n"):
                if voltage_in_line.find("Volt_") != -1:
                    oneVoltageValues = voltage_in_line.replace(" ","").split("|")
                    all_voltage_value_dic[oneVoltageValues[0]] = {"Health": oneVoltageValues[2], 
                                                                  "MemberId": oneVoltageValues[3], 
                                                                  "ReadingVolts": oneVoltageValues[4].split("%")[0]}
            voltage_return_dic[node_id] = all_voltage_value_dic
            
        except Exception, e:
            self.log('ERROR', "Node {} IP {}: Error happens when construct the voltage value dictionary. Fail reason: {}".format(node_id, bmc_ip, str(e)))

    def voltage_get_value_by_telnet(self, node_id, bmc_ip, sensor_ID="0xda"):
        """
        Steps of this test case: 
            1. telnet to the compute node with <telnet bmc_ip 9300>. 
            2. Send "sensor value get <sensor ID>" and get the response. The result would like below: 
                IPMI_SIM> sensor value get 0xda
                Volt_VR_CPU0 : : 1.800 Volts
            3. Analysis the result in 2 and then return the value of Voltage sensor.

        @node_id: compute node id
        @bmc_ip: bmc ip address
        @sensor_ID: the sensor that you want to change value.
        @return: the Voltage value or raise an exception when cannot get the Voltage.
        """
        str_telnet = "telnet " + bmc_ip + " 9300"
        voltage_value_get = "sensor value get {}".format(sensor_ID)
        str_quit = "quit"
        
        # Telnet to the node by <telnet bmc_ip 9300>
        try:
            self.ssh.start_cache()
            ssh_log = self.ssh.send_command_wait_string(str_command= str_telnet + chr(13),
                                                        wait='IPMI_SIM',
                                                        int_time_out=120,
                                                        b_with_buff=False)
            self.log('DEBUG', ssh_log)
        except Exception, e:
            self.log('ERROR', "Node {} with IP {} fail to telnet. Fail Reason: {}".format(node_id, bmc_ip, str(e)))

        voltage_value_output = ""
        try:
            # Send "sensor value get <sensor ID>" command and get the result.
            self.ssh.start_cache()
            self.ssh.send_command(voltage_value_get + chr(13))
            time.sleep(1)
            voltage_value_output = self.ssh.get_cache()
            self.log('DEBUG', voltage_value_output)
        except Exception, e:
            self.log('ERROR', "Node {} with IP {} fail to get the Voltage value. Fail reason: {}".format(node_id, bmc_ip,str(e)))
        finally:
            # close the telnet 
            self.ssh.start_cache()
            self.ssh.send_command(str_quit + chr(13))
            time.sleep(1)
            self.log('DEBUG', self.ssh.get_cache())

        # Handle the voltage_value_output and then get the value of <sensor_ID>. 
        if voltage_value_output == "":
            raise ValueError("Node {} with IP {} fail to get the Voltage value.".format(node_id, bmc_ip))

        voltage_value = ""
        for voltage_value_output_in_line in voltage_value_output.split("\n"):
            if voltage_value_output_in_line.find("Volt_") != -1:
                voltage_value = voltage_value_output_in_line.replace(" ","").split(":")[1]
                self.log('INFO', "The Original Voltage value for Sensor {}: {}".format(sensor_ID, voltage_value))
        if voltage_value == "":
            raise ValueError("Node {} with IP {} fail to get the Voltage value.".format(node_id, bmc_ip))
            return
        return voltage_value

    def voltage_change_value_by_telnet(self, node_id, bmc_ip, value_to_change="6.6", sensor_ID="0xda"):
        """
        change the voltage value of <sensor_ID> by <telnet bmc_ip 9300>. 
        Steps of this test case: 
            1. telnet to the compute node with <telnet bmc_ip 9300>. 
            2. Send "sensor value set <sensor_ID> <value_to_change>".

        @node_id: compute node id
        @bmc_ip: bmc ip address
        @value_to_change: the voltage value that you want to change.
        @sensor_ID: the sensor that you want to change value.
        """
        str_telnet = "telnet " + bmc_ip + " 9300"
        voltage_value_set = "sensor value set {} {}".format(sensor_ID, value_to_change)
        str_quit = "quit"
        
        # Telnet to the node by <telnet bmc_ip 9300> and then change one voltage value
        self.ssh.start_cache()
        try:
            telnet_log = self.ssh.send_command_wait_string(str_command= str_telnet + chr(13),
                                                           wait='IPMI_SIM',
                                                           int_time_out=120,
                                                           b_with_buff=False)
            self.log('DEBUG', telnet_log)
        except Exception, e:
            self.log('ERROR', "Node {} with IP {} fail to telnet. Fail Reason: {}".format(node_id, bmc_ip, str(e)))

        # Change the <sensor_ID> value
        try:
            self.ssh.start_cache()
            self.ssh.send_command(voltage_value_set + chr(13))
            time.sleep(1)
            self.log('DEBUG', self.ssh.get_cache())
        except Exception, e:
            self.log('ERROR', "Node {} with IP {} fail to change the Voltage value. Fail reason: {}".format(node_id, bmc_ip,str(e)))
        finally:
            # close the telnet 
            self.ssh.start_cache()
            self.ssh.send_command(str_quit + chr(13))
            time.sleep(1)
            self.log('DEBUG', self.ssh.get_cache())
