# -*- coding: utf-8 -*-
"""
Copyright (C) 2026 Oliver Tengler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Tests for AgentState start/stop helpers.
"""

import unittest
from unittest import mock


class TestAgentState(unittest.TestCase):
    """Tests for the central agent server start/stop helpers."""

    def setUp(self) -> None:
        from .. import AgentState
        self.AgentState = AgentState
        self.AgentState.setAgentServer(None)
        self.AgentState._externalServerRunning = False

    def tearDown(self) -> None:
        self.AgentState.setAgentServer(None)
        self.AgentState._externalServerRunning = False

    def _mockAppConfig(self) -> mock.MagicMock:
        """Return a mock appConfig whose agent section points at the default port."""
        appConfig = mock.MagicMock()
        appConfig.agent.bind = "127.0.0.1"
        appConfig.agent.port = 8080
        return appConfig

    def test_startStartsServerAndRegistersIt(self) -> None:
        with mock.patch("ai_agent.AgentState.AgentServer") as serverClass:
            serverClass.return_value.start.return_value = True
            self.assertTrue(self.AgentState.startAgentServer(8080))
            serverClass.return_value.start.assert_called_once()
            self.assertIs(self.AgentState.agentServer(), serverClass.return_value)

    def test_startFailureReturnsFalse(self) -> None:
        with mock.patch("ai_agent.AgentState.AgentServer") as serverClass:
            serverClass.return_value.start.return_value = False
            self.assertFalse(self.AgentState.startAgentServer(8080))
            self.assertIsNone(self.AgentState.agentServer())

    def test_startDoesNotRestartRunningServer(self) -> None:
        with mock.patch("ai_agent.AgentState.AgentServer") as serverClass:
            serverClass.return_value.start.return_value = True
            self.assertTrue(self.AgentState.startAgentServer(8080))
            self.assertTrue(self.AgentState.startAgentServer(8080))
            self.assertEqual(serverClass.return_value.start.call_count, 1)

    def test_stopStopsAndUnregistersServer(self) -> None:
        with mock.patch("ai_agent.AgentState.AgentServer") as serverClass:
            serverClass.return_value.start.return_value = True
            self.assertTrue(self.AgentState.startAgentServer(8080))
            self.AgentState.stopAgentServer()
            serverClass.return_value.stop.assert_called_once()
            self.assertIsNone(self.AgentState.agentServer())

    def test_stopWithoutServerIsNoOp(self) -> None:
        self.AgentState.stopAgentServer()
        self.assertIsNone(self.AgentState.agentServer())

    def test_startDoesNotStartWhenExternalServerRunning(self) -> None:
        with mock.patch("ai_agent.AgentState.AgentServer") as serverClass:
            self.AgentState._externalServerRunning = True
            try:
                self.assertTrue(self.AgentState.startAgentServer(8080))
                serverClass.return_value.start.assert_not_called()
                self.assertIsNone(self.AgentState.agentServer())
            finally:
                self.AgentState._externalServerRunning = False

    def test_applyChangesDoesNotTouchServerWhenExternalRunning(self) -> None:
        with mock.patch("ai_agent.AgentState.AgentServer") as serverClass:
            serverClass.return_value.start.return_value = True
            self.AgentState._externalServerRunning = True
            try:
                self.assertTrue(self.AgentState.applyAgentServerChanges(True, 8080))
                serverClass.return_value.start.assert_not_called()
                self.assertTrue(self.AgentState.applyAgentServerChanges(False, 8080))
                self.assertIsNone(self.AgentState.agentServer())
            finally:
                self.AgentState._externalServerRunning = False

    def test_checkExternalAgentServerDetectsHealthEndpoint(self) -> None:
        response = mock.MagicMock()
        response.status = 200
        response.__enter__.return_value = response  # context manager returns itself
        with mock.patch("ai_agent.AgentState.appConfig",
                        return_value=self._mockAppConfig()), \
             mock.patch("ai_agent.AgentState.urllib.request.urlopen",
                        return_value=response) as urlopen:
            self.assertTrue(self.AgentState.checkExternalAgentServer())
            urlopen.assert_called_once()
            # The probe must carry excludeFromHistory so that it is not recorded
            # in the API history of the external server.
            url = urlopen.call_args[0][0]
            self.assertIn("excludeFromHistory=1", url)
            self.assertTrue(self.AgentState.externalServerRunning())

    def test_checkExternalAgentServerNoServer(self) -> None:
        with mock.patch("ai_agent.AgentState.appConfig",
                        return_value=self._mockAppConfig()), \
             mock.patch("ai_agent.AgentState.urllib.request.urlopen",
                        side_effect=OSError("connection refused")):
            self.assertFalse(self.AgentState.checkExternalAgentServer())
            self.assertFalse(self.AgentState.externalServerRunning())

    def test_fetchExternalHistoryParsesEntries(self) -> None:
        body = (b'{"history": ['
                b'{"timestamp": 200.0, "method": "POST", "path": "/search/content", '
                b'"params": "query: \'x\'", "statusCode": 200, "durationSecs": 1.5}]}')
        response = mock.MagicMock()
        response.status = 200
        response.read.return_value = body
        response.__enter__.return_value = response
        self.AgentState._externalServerRunning = True
        try:
            with mock.patch("ai_agent.AgentState.appConfig",
                            return_value=self._mockAppConfig()), \
                 mock.patch("ai_agent.AgentState.urllib.request.urlopen",
                            return_value=response) as urlopen:
                entries = self.AgentState.fetchExternalHistory()
            urlopen.assert_called_once()
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(entry.method, "POST")
            self.assertEqual(entry.path, "/search/content")
            self.assertEqual(entry.params, "query: 'x'")
            self.assertEqual(entry.statusCode, 200)
            self.assertEqual(entry.durationSecs, 1.5)
        finally:
            self.AgentState._externalServerRunning = False

    def test_fetchExternalHistoryNoExternalServer(self) -> None:
        self.AgentState._externalServerRunning = False
        with mock.patch("ai_agent.AgentState.urllib.request.urlopen") as urlopen:
            self.assertEqual(self.AgentState.fetchExternalHistory(), [])
            urlopen.assert_not_called()

    def test_fetchExternalHistoryFailureReturnsEmpty(self) -> None:
        self.AgentState._externalServerRunning = True
        try:
            with mock.patch("ai_agent.AgentState.appConfig",
                            return_value=self._mockAppConfig()), \
                 mock.patch("ai_agent.AgentState.urllib.request.urlopen",
                            side_effect=OSError("connection refused")):
                self.assertEqual(self.AgentState.fetchExternalHistory(), [])
        finally:
            self.AgentState._externalServerRunning = False