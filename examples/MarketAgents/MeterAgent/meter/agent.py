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

import sys
import logging
from volttron.platform.agent import utils
from volttron.platform.agent.base_market_agent import MarketAgent
from volttron.platform.agent.base_market_agent.poly_line import PolyLine
from volttron.platform.agent.base_market_agent.point import Point
from volttron.platform.agent.base_market_agent.buy_sell import SELLER

_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.01"

def meter_agent(config_path, **kwargs):
    """Parses the Electric Meter Agent configuration and returns an instance of
    the agent created using that configuation.

    :param config_path: Path to a configuation file.

    :type config_path: str
    :returns: Market Service Agent
    :rtype: MarketServiceAgent
    """
    _log.debug("Starting MeterAgent")
    try:
        config = utils.load_config(config_path)
    except Exception:
        config = {}

    if not config:
        _log.info("Using defaults for starting configuration.")

    market_name = config.get('market_name', 'electric')
    price = config.get('price', 55)
    verbose_logging= config.get('verbose_logging', True)
    return MeterAgent(market_name, price, verbose_logging, **kwargs)


class MeterAgent(MarketAgent):
    """
    The SampleElectricMeterAgent serves as a sample of an electric meter that
    sells electricity for a single building at a fixed price.
    """
    def __init__(self, market_name, price, verbose_logging, **kwargs):
        super(MeterAgent, self).__init__(verbose_logging, **kwargs)
        self.market_name = market_name
        self.price = price
        self.infinity=1000000
        self.num=0
        self.want_reservation = True
        self.join_market(self.market_name, SELLER, self.reservation_callback, self.offer_callback, None, self.price_callback, self.error_callback)

    def offer_callback(self, timestamp, market_name, buyer_seller):
        if self.has_reservation:
            curve = self.create_supply_curve()
            _log.debug("Offer for Market: {} {}, Curve: {}".format(market_name, buyer_seller, curve))
            self.make_offer(market_name, buyer_seller, curve)
        else:
            _log.debug("No offer for Market: {} {}".format(market_name, buyer_seller))


		
    def reservation_callback(self, timestamp, market_name, buyer_seller):
        if (self.num % 2) == 0:
            self.want_reservation = True
        else:
            self.want_reservation = False
        _log.debug("Reservation for Market: {} {}, Wants reservation: {} Number: {}".format(market_name, buyer_seller, self.want_reservation, self.num))
        self.num = (self.num + 1) % 256 # We don't want this number to get very large.
        return self.want_reservation

		
    def create_supply_curve(self):
        supply_curve = PolyLine()
        price = self.price
        quantity = self.infinity
        supply_curve.add(Point(price=price, quantity=quantity))
        price = self.price
        quantity = 0
        supply_curve.add(Point(price=price, quantity=quantity))
        return supply_curve

    def price_callback(self, timestamp, market_name, buyer_seller, price, quantity):
        _log.debug("Report the new cleared price for Market: {} {}, Message: {}".format(market_name, buyer_seller, price, quantity))

    def error_callback(self, timestamp, market_name, buyer_seller, error_code, error_message, aux):
        _log.debug("Report error for Market: {} {}, Code: {}, Message: {}".format(market_name, buyer_seller, error_code, error_message))

def main():
    """Main method called to start the agent."""
    utils.vip_main(meter_agent, version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
