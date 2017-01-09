# Copyright (c) 2012, Benjamin Vanheuverzwijn <bvanheu@gmail.com>
# All rights reserved.
#
# Thanks to Marc-Etienne M. Leveille
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
# DISCLAIMED. IN NO EVENT SHALL Benjamin Vanheuverzwijn BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import requests
import toutv.exceptions
import toutv.mapper
import toutv.config
import toutv.bos as bos


class Transport:

    def get_emissions(self):
        raise NotImplementedError()

    def get_emission_episodes(self, emission_id):
        raise NotImplementedError()

    def get_page_repertoire(self):
        raise NotImplementedError()

    def search_terms(self, query):
        raise NotImplementedError()


class JsonTransport(Transport):

    def __init__(self, proxies=None, auth=None):
        self._mapper = toutv.mapper.JsonMapper()

        self.set_proxies(proxies)
        self.set_auth(auth)

    def set_proxies(self, proxies):
        self._proxies = proxies

    def set_auth(self, auth):
        self._auth = auth

    def _do_query_url(self, url, params={}, timeout=20):
        try:
            headers = toutv.config.HEADERS

            r = requests.get(url, params=params, headers=headers,
                             proxies=self._proxies, timeout=timeout)
            if r.status_code != 200:
                code = r.status_code
                raise toutv.exceptions.UnexpectedHttpStatusCodeError(url, code)

            return r
        except requests.exceptions.Timeout:
            raise toutv.exceptions.RequestTimeoutError(url, timeout)

    def _do_query_json_url(self, url, params={}):
        r = self._do_query_url(url, params)
        return r.json()

    def _do_query_json_endpoint(self, endpoint, params={}):
        url = '{}{}'.format(toutv.config.TOUTV_JSON_URL_PREFIX, endpoint)
        json = self._do_query_json_url(url, params)
        return json['d']

    def get_emissions(self):
        emissions = []

        # All emissions, including those only available in Extra
        # We don't have much information about them, except their id, title, and URL, but that is enough to be able to fetch them at least.
        url = '{}/presentation/search'.format(toutv.config.TOUTV_BASE_URL)
        params = {'v': 2, 'd': 'android'}
        results_dto = self._do_query_json_url(url, params)

        def dto_to_bo(dto):
            bo = toutv.bos.Emission()

            bo.Title = dto['DisplayText']
            bo.Id = dto['Id']
            bo.Url = dto['Url']

            return bo

        def filter_program(dto):
            return dto['Key'].startswith('program-')

        programs_dto = filter(filter_program, results_dto)
        emissions = map(dto_to_bo, programs_dto)

        return list(emissions)

    def get_emission_episodes(self, emission, short_version=False):
        if short_version:
            if len(emission.get_episodes()) > 0:
                return emission.get_episodes()

        episodes = {}

        url = '{}/presentation/{}'.format(toutv.config.TOUTV_BASE_URL, emission.Url)
        params = {'v': 2, 'excludeLineups': False, 'd': 'android'}
        emission_dto = self._do_query_json_url(url, params)
        seasons = emission_dto['SeasonLineups']
        for season in seasons:
            episodes_dto = season['LineupItems']
            for episode_dto in episodes_dto:
                episode = toutv.bos.Episode()
                episode.Title = episode_dto['Title']
                episode.Description = episode_dto['Description']
                if 'Description' in episode_dto['Details']:
                    episode.Description = episode_dto['Details']['Description']
                episode.PID = episode_dto['IdMedia']
                episode.Id = episode_dto['Key'][6:]
                episode.Url = episode_dto['Url']
                episode.AirDateLongString = episode_dto['Details']['AirDate']
                episode.CategoryId = emission.Id
                episode.SeasonAndEpisode = toutv.client.Client._find_last(r'/.*/(.*)$', episode_dto['Url'])
                episode.set_emission(emission)
                episodes[episode.Id] = episode

        if len(episodes) == 0:
            params = {'emissionid': str(emission.Id)}
            episodes_dto = self._do_query_json_endpoint('GetEpisodesForEmission', params)
            for episode_dto in episodes_dto:
                episode = self._mapper.dto_to_bo(episode_dto, bos.Episode)
                episode.set_emission(emission)
                episodes[episode.Id] = episode

        return episodes

    def get_page_repertoire(self):
        repertoire_dto = self._do_query_json_endpoint('GetPageRepertoire')

        repertoire = bos.Repertoire()

        # Emissions
        if 'Emissions' in repertoire_dto:
            repertoire.Emissions = {}
            emissionrepertoires_dto = repertoire_dto['Emissions']
            for emissionrepertoire_dto in emissionrepertoires_dto:
                er = self._mapper.dto_to_bo(emissionrepertoire_dto,
                                            bos.EmissionRepertoire)
                repertoire.Emissions[er.Id] = er

        # Genre
        if 'Genres' in repertoire_dto:
            # TODO: implement
            pass

        # Country
        if 'Pays' in repertoire_dto:
            # TODO: implement
            pass

        return repertoire

    def search(self, query):
        searchresults = None
        searchresultdatas = []
        params = {'query': query}

        searchresults_dto = self._do_query_json_endpoint('SearchTerms', params)

        searchresults = self._mapper.dto_to_bo(searchresults_dto,
                                               bos.SearchResults)
        if searchresults.Results is not None:
            for searchresultdata_dto in searchresults.Results:
                sr_bo = self._mapper.dto_to_bo(searchresultdata_dto,
                                               bos.SearchResultData)
                searchresultdatas.append(sr_bo)
        searchresults.Results = searchresultdatas

        return searchresults
