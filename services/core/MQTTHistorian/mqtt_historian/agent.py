# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:
#
# Copyright 2020, Battelle Memorial Institute.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This material was prepared as an account of work sponsored by an agency of
# the United States Government. Neither the United States Government nor the
# United States Department of Energy, nor Battelle, nor any of their
# employees, nor any jurisdiction or organization that has cooperated in the
# development of these materials, makes any warranty, express or
# implied, or assumes any legal liability or responsibility for the accuracy,
# completeness, or usefulness or any information, apparatus, product,
# software, or process disclosed, or represents that its use would not infringe
# privately owned rights. Reference herein to any specific commercial product,
# process, or service by trade name, trademark, manufacturer, or otherwise
# does not necessarily constitute or imply its endorsement, recommendation, or
# favoring by the United States Government or any agency thereof, or
# Battelle Memorial Institute. The views and opinions of authors expressed
# herein do not necessarily state or reflect those of the
# United States Government or any agency thereof.
#
# PACIFIC NORTHWEST NATIONAL LABORATORY operated by
# BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY
# under Contract DE-AC05-76RL01830
# }}}


import datetime
import logging
import sys
import time

from volttron.platform import jsonapi
from volttron.platform.agent.base_historian import BaseHistorian
from volttron.platform.agent import utils

from paho.mqtt.client import MQTTv311, MQTTv31
import paho.mqtt.publish as publish


utils.setup_logging()
_log = logging.getLogger(__name__)
__version__ = '0.2'


def historian(config_path, **kwargs):
    if isinstance(config_path, dict):
        config_dict = config_path
    else:
        config_dict = utils.load_config(config_path)

    connection = config_dict.get('connection', None)
    assert connection is not None

    utils.update_kwargs_with_config(kwargs, config_dict)

    return MQTTHistorian(**kwargs)


class MQTTHistorian(BaseHistorian):
    """
    This historian publishes data to a MQTT Broker.
    """

    def __init__(self, connection, **kwargs):
        # We pass every optional parameter to the MQTT library functions so they
        # default to the same values that paho uses as defaults.
        self.mqtt_qos = connection.get('mqtt_qos', 0)
        self.mqtt_retain = connection.get('mqtt_retain', False)

        self.mqtt_hostname = connection.get('mqtt_hostname', 'localhost')
        self.mqtt_port = connection.get('mqtt_port', 1883)
        self.mqtt_client_id = connection.get('mqtt_client_id', '')
        self.mqtt_keepalive = connection.get('mqtt_keepalive', 60)
        self.mqtt_will = connection.get('mqtt_will', None)
        self.mqtt_auth = connection.get('mqtt_auth', None)
        self.mqtt_tls = connection.get('mqtt_tls', None)

        protocol = connection.get('mqtt_protocol', MQTTv311)
        if protocol == "MQTTv311":
            protocol = MQTTv311
        elif protocol == "MQTTv31":
            protocol = MQTTv31

        if protocol not in (MQTTv311, MQTTv31):
            raise ValueError("Unknown MQTT protocol: {}".format(protocol))

        self.mqtt_protocol = protocol

        # will be available in both threads.
        self._last_error = 0

        super(MQTTHistorian, self).__init__(**kwargs)

    def timestamp(self):
        return time.mktime(datetime.datetime.now().timetuple())

    def publish_to_historian(self, to_publish_list):
        _log.debug("publish_to_historian number of items: {}".format(len(to_publish_list)))
        if self._last_error:
            # if we failed we need to wait 60 seconds before we go on.
            if self.timestamp() < self._last_error + 60:
                _log.debug('Not allowing send < 60 seconds from failure')
                return

        to_send = []
        for x in to_publish_list:
            topic = x['topic']

            # Construct payload from data in the publish item.
            # Available fields: 'value', 'headers', and 'meta'
            payload = jsonapi.dumps(x['value'])
            _log.debug(f'payload: {payload}, topic {topic}')

            to_send.append({'topic': topic,
                            'payload': payload,
                            'qos': self.mqtt_qos,
                            'retain': self.mqtt_retain})

        try:
            publish.multiple(to_send,
                             hostname=self.mqtt_hostname,
                             port=self.mqtt_port,
                             client_id=self.mqtt_client_id,
                             keepalive=self.mqtt_keepalive,
                             will=self.mqtt_will,
                             auth=self.mqtt_auth,
                             tls=self.mqtt_tls,
                             protocol=self.mqtt_protocol)
            self.report_all_handled()
        except Exception as e:
            _log.warning("Exception ({}) raised by publish: {}".format(e.__class__.__name__, e))
            self._last_error = self.timestamp()


def main(argv=sys.argv):
    try:
        utils.vip_main(historian, version=__version__)
    except Exception as e:
        print(e)
        _log.exception('unhandled exception')


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
