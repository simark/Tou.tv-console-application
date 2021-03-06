# Copyright (c) 2015, Benjamin Vanheuverzwijn <bvanheu@gmail.com>
# All rights reserved.
#
# Gladly lifted from my friend Simon Carpentier <simon.carpentier@spacebar.ca>
#   https://github.com/scarpentier/toutv-extra
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of pytoutv nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Benjamin Vanheuverzwijn OR Philippe Proulx
# BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re
import requests
import toutv.config
import toutv.exceptions

class Auth:

    def __init__(self, token=None):
        self._token = token

    def get_claims(self, token):
        headers = {
                "Authorization"     : "Bearer " + token,
                "User-Agent"        : toutv.config.USER_AGENT,
                "Accept"            : "application/json",
                "Host"              : "services.radio-canada.ca",
                }

        r = requests.get(toutv.config.TOUTV_AUTH_CLAIMS_URL.format(token), headers=headers)

        if r.status_code != 200:
            raise toutv.exceptions.UnexpectedHttpStatusCodeError(toutv.config.TOUTV_AUTH_CLAIMS_URL.format(token), r.status_code)

        return r.json()["claims"]

    def get_token(self):
        return self._token

    def login(self, username, password):
        sessionid = self._get_sessionid()

        payload = {
                "sessionID": sessionid,
                "action": "login",
                "client_id": toutv.config.TOUTV_AUTH_CLIENT_ID,
                "redirect_uri" : "http://ici.tou.tv/login/loginCallback",
                "client-domain": "icitv",
                "client-platform": "android",
                "login-email": username,
                "login-password": password,
                "form-submit-btn": "Ouvrir une session"
                }

        headers = {
                "User-Agent"        : toutv.config.USER_AGENT,
                "Accept"            : "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Origin"            : "https://services.radio-canada.ca",
                "X-Requested-With"  : "tv.tou.android",
                "Referer"           : toutv.config.TOUTV_AUTH_SESSION_URL,
                "Content-type"      : "application/x-www-form-urlencoded",
                }

        r = requests.post(toutv.config.TOUTV_AUTH_TOKEN_URL, headers=headers, data=payload, allow_redirects=False)

        if r.status_code != 302:
            raise toutv.exceptions.UnexpectedHttpStatusCodeError(toutv.config.TOUTV_AUTH_TOKEN_URL, r.status_code)

        self._token = re.search("access_token=([^&]*)", r.headers["Location"]).group(1)

    def _get_sessionid(self):
        headers = {
                "User-Agent"        : toutv.config.USER_AGENT,
                "Accept"            : "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Origin"            : "https://services.radio-canada.ca",
                "X-Requested-With"  : "tv.tou.android"
                }

        r = requests.get(toutv.config.TOUTV_AUTH_SESSION_URL, headers=headers)

        if r.status_code != 200:
            raise toutv.exceptions.UnexpectedHttpStatusCodeError(toutv.config.TOUTV_AUTH_SESSION_URL, r.status_code)

        sessionId = re.search("name=\"sessionID\" value=\"([^\"]*)\"", r.text).group(1)

        return sessionId

