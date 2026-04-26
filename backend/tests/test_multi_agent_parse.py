"""Unit tests for multi_agent.py — parsing functions.

Tests are written before implementation (TDD). All tests must fail before
implementation exists.
"""

import json

import pytest

# ---------------------------------------------------------------------------
# _parse_specialist — happy path
# ---------------------------------------------------------------------------


class TestParseSpecialistHappyPath:
    def test_valid_json_returns_specialist_diagnosis(self) -> None:
        """_parse_specialist returns a SpecialistDiagnosis with correct fields."""
        from lib.diagnosis.multi_agent import SpecialistDiagnosis, _parse_specialist

        text = json.dumps(
            {
                "region": "bust",
                "issues": [
                    {
                        "issue_type": "pulling_across_bust",
                        "confidence": 0.85,
                        "description": "Horizontal pull lines across bust",
                        "recommended_adjustment": "Add FBA",
                    }
                ],
            }
        )
        result = _parse_specialist("bust", text)

        assert isinstance(result, SpecialistDiagnosis)
        assert result.region == "bust"
        assert len(result.issues) == 1
        issue = result.issues[0]
        assert issue.issue_type == "pulling_across_bust"
        assert issue.confidence == 0.85
        assert issue.description == "Horizontal pull lines across bust"
        assert issue.recommended_adjustment == "Add FBA"

    def test_confidence_clamped_above_1(self) -> None:
        """_parse_specialist clamps confidence > 1.0 to 1.0."""
        from lib.diagnosis.multi_agent import _parse_specialist

        text = json.dumps(
            {
                "region": "waist_hip",
                "issues": [
                    {
                        "issue_type": "excess_fabric",
                        "confidence": 1.5,
                        "description": "Too much fabric",
                        "recommended_adjustment": "Take in at waist",
                    }
                ],
            }
        )
        result = _parse_specialist("waist_hip", text)
        assert result.issues[0].confidence == 1.0

    def test_confidence_clamped_below_0(self) -> None:
        """_parse_specialist clamps confidence < 0.0 to 0.0."""
        from lib.diagnosis.multi_agent import _parse_specialist

        text = json.dumps(
            {
                "region": "back",
                "issues": [
                    {
                        "issue_type": "swayback",
                        "confidence": -0.2,
                        "description": "Pooling at lower back",
                        "recommended_adjustment": "Swayback adjustment",
                    }
                ],
            }
        )
        result = _parse_specialist("back", text)
        assert result.issues[0].confidence == 0.0

    def test_confidence_exactly_at_boundary_unchanged(self) -> None:
        """_parse_specialist does not alter confidence values at 0.0 or 1.0."""
        from lib.diagnosis.multi_agent import _parse_specialist

        for confidence in [0.0, 1.0]:
            text = json.dumps(
                {
                    "region": "bust",
                    "issues": [
                        {
                            "issue_type": "test",
                            "confidence": confidence,
                            "description": "test",
                            "recommended_adjustment": "test",
                        }
                    ],
                }
            )
            result = _parse_specialist("bust", text)
            assert result.issues[0].confidence == confidence

    def test_empty_issues_list_valid(self) -> None:
        """_parse_specialist accepts an empty issues list."""
        from lib.diagnosis.multi_agent import SpecialistDiagnosis, _parse_specialist

        text = json.dumps({"region": "bust", "issues": []})
        result = _parse_specialist("bust", text)
        assert isinstance(result, SpecialistDiagnosis)
        assert result.issues == []

    def test_multiple_issues_parsed(self) -> None:
        """_parse_specialist parses multiple issues correctly."""
        from lib.diagnosis.multi_agent import _parse_specialist

        text = json.dumps(
            {
                "region": "back",
                "issues": [
                    {
                        "issue_type": "swayback",
                        "confidence": 0.9,
                        "description": "Lower back pooling",
                        "recommended_adjustment": "Swayback adjustment",
                    },
                    {
                        "issue_type": "shoulder_blade_gap",
                        "confidence": 0.4,
                        "description": "Gap at shoulder blades",
                        "recommended_adjustment": "Add ease at back",
                    },
                ],
            }
        )
        result = _parse_specialist("back", text)
        assert len(result.issues) == 2
        assert result.issues[0].issue_type == "swayback"
        assert result.issues[1].issue_type == "shoulder_blade_gap"


# ---------------------------------------------------------------------------
# _parse_specialist — error cases
# ---------------------------------------------------------------------------


class TestParseSpecialistErrors:
    def test_malformed_json_raises_specialist_parse_error(self) -> None:
        """_parse_specialist raises SpecialistParseError on malformed JSON."""
        from lib.diagnosis.multi_agent import SpecialistParseError, _parse_specialist

        text = "This is not JSON at all"
        with pytest.raises(SpecialistParseError) as exc_info:
            _parse_specialist("bust", text)

        assert "This is not JSON at all" in str(exc_info.value)

    def test_missing_issues_field_raises_specialist_parse_error(self) -> None:
        """_parse_specialist raises SpecialistParseError when 'issues' key is absent."""
        from lib.diagnosis.multi_agent import SpecialistParseError, _parse_specialist

        text = json.dumps({"region": "bust"})  # missing 'issues'
        with pytest.raises(SpecialistParseError) as exc_info:
            _parse_specialist("bust", text)

        assert text in str(exc_info.value)

    def test_missing_region_field_raises_specialist_parse_error(self) -> None:
        """_parse_specialist raises SpecialistParseError when 'region' key is absent."""
        from lib.diagnosis.multi_agent import SpecialistParseError, _parse_specialist

        text = json.dumps({"issues": []})  # missing 'region'
        with pytest.raises(SpecialistParseError) as exc_info:
            _parse_specialist("bust", text)

        assert text in str(exc_info.value)

    def test_issue_missing_required_field_raises_specialist_parse_error(self) -> None:
        """_parse_specialist raises SpecialistParseError when an issue is missing a required field."""
        from lib.diagnosis.multi_agent import SpecialistParseError, _parse_specialist

        text = json.dumps(
            {
                "region": "bust",
                "issues": [
                    {
                        "issue_type": "pulling",
                        # missing confidence, description, recommended_adjustment
                    }
                ],
            }
        )
        with pytest.raises(SpecialistParseError) as exc_info:
            _parse_specialist("bust", text)

        assert text in str(exc_info.value)

    def test_parse_error_includes_offending_text(self) -> None:
        """SpecialistParseError includes the offending text in its message."""
        from lib.diagnosis.multi_agent import SpecialistParseError, _parse_specialist

        offending = "not valid json {"
        with pytest.raises(SpecialistParseError) as exc_info:
            _parse_specialist("back", offending)

        assert offending in str(exc_info.value)


# ---------------------------------------------------------------------------
# _parse_coordinator — happy path and error cases
# ---------------------------------------------------------------------------


class TestParseCoordinator:
    def test_valid_coordinator_response_returns_diagnosis_result(self) -> None:
        """_parse_coordinator returns DiagnosisResult with correct fields."""
        from lib.diagnosis.multi_agent import DiagnosisResult, _parse_coordinator

        text = json.dumps(
            {
                "issues": [
                    {
                        "issue_type": "pulling_across_bust",
                        "confidence": 0.9,
                        "description": "Horizontal pull lines",
                        "recommended_adjustment": "Full bust adjustment",
                    }
                ],
                "primary_recommendation": "Perform a full bust adjustment",
                "cascade_type": "fba",
            }
        )
        result = _parse_coordinator(text)

        assert isinstance(result, DiagnosisResult)
        assert result.cascade_type == "fba"
        assert result.primary_recommendation == "Perform a full bust adjustment"
        assert len(result.issues) == 1

    def test_cascade_type_swayback_valid(self) -> None:
        """_parse_coordinator accepts cascade_type 'swayback'."""
        from lib.diagnosis.multi_agent import DiagnosisResult, _parse_coordinator

        text = json.dumps(
            {
                "issues": [],
                "primary_recommendation": "Swayback adjustment recommended",
                "cascade_type": "swayback",
            }
        )
        result = _parse_coordinator(text)
        assert isinstance(result, DiagnosisResult)
        assert result.cascade_type == "swayback"

    def test_cascade_type_none_valid(self) -> None:
        """_parse_coordinator accepts cascade_type 'none'."""
        from lib.diagnosis.multi_agent import _parse_coordinator

        text = json.dumps(
            {
                "issues": [],
                "primary_recommendation": "No adjustments needed",
                "cascade_type": "none",
            }
        )
        result = _parse_coordinator(text)
        assert result.cascade_type == "none"

    def test_bad_cascade_type_raises_coordinator_parse_error(self) -> None:
        """_parse_coordinator raises CoordinatorParseError for invalid cascade_type."""
        from lib.diagnosis.multi_agent import CoordinatorParseError, _parse_coordinator

        text = json.dumps(
            {
                "issues": [],
                "primary_recommendation": "Some recommendation",
                "cascade_type": "banana",
            }
        )
        with pytest.raises(CoordinatorParseError):
            _parse_coordinator(text)

    def test_malformed_json_raises_coordinator_parse_error(self) -> None:
        """_parse_coordinator raises CoordinatorParseError on malformed JSON."""
        from lib.diagnosis.multi_agent import CoordinatorParseError, _parse_coordinator

        with pytest.raises(CoordinatorParseError):
            _parse_coordinator("this is not json")

    def test_missing_cascade_type_raises_coordinator_parse_error(self) -> None:
        """_parse_coordinator raises CoordinatorParseError when cascade_type is absent."""
        from lib.diagnosis.multi_agent import CoordinatorParseError, _parse_coordinator

        text = json.dumps(
            {
                "issues": [],
                "primary_recommendation": "Some recommendation",
                # missing cascade_type
            }
        )
        with pytest.raises(CoordinatorParseError):
            _parse_coordinator(text)


# ---------------------------------------------------------------------------
# spec 24 — neck_collar region parsing
# ---------------------------------------------------------------------------


class TestParseSpecialistNeckCollar:
    def test_parse_specialist_neck_collar_returns_correct_region(self) -> None:
        """_parse_specialist returns a SpecialistDiagnosis with region == 'neck_collar'."""
        from lib.diagnosis.multi_agent import SpecialistDiagnosis, _parse_specialist

        valid_json = json.dumps(
            {
                "region": "neck_collar",
                "issues": [
                    {
                        "issue_type": "cb_neckline_gaping",
                        "confidence": 0.8,
                        "description": "Collar lifts away from the back of the neck at CB",
                        "recommended_adjustment": "Deepen the back neck curve on the pattern at CB",
                    }
                ],
            }
        )

        result = _parse_specialist("neck_collar", valid_json)

        assert isinstance(result, SpecialistDiagnosis)
        assert result.region == "neck_collar"
        assert len(result.issues) == 1
        assert result.issues[0].issue_type == "cb_neckline_gaping"
