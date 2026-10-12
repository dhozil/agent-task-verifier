"""Direct-mode tests for the AgentTaskVerifier contract."""

import json
import re

from gltest.direct import create_address

TASK_TITLE = "Write API Documentation"
TASK_SPEC = "Write comprehensive API docs for the REST endpoints. Include examples."
DELIVERABLE_URL = "https://docs.example.com/api"
DELIVERABLE_DESC = "Complete API documentation with examples"
PASS_JSON = json.dumps(
    {"decision": "pass", "reasoning": "Documentation covers all endpoints with examples.", "completeness_score": 90, "confidence": 95}
)
FAIL_JSON = json.dumps(
    {"decision": "fail", "reasoning": "Documentation missing several endpoints.", "completeness_score": 40, "confidence": 85}
)


def _create_task(contract, vm, creator, agent_addr=None):
    vm.sender = creator
    return contract.create_task(
        title=TASK_TITLE, specification=TASK_SPEC,
        agent_address=agent_addr or str(create_address("agent")),
        deadline_days=7,
    )


def test_create_task_validates(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/agent_task_verifier.py")
    creator = create_address("creator")

    direct_vm.sender = creator
    with direct_vm.expect_revert("Title and specification are required"):
        contract.create_task("", "spec", str(create_address("agent")), 7)
    with direct_vm.expect_revert("Agent address is required"):
        contract.create_task("T", "spec", "", 7)
    with direct_vm.expect_revert("Deadline must be at least 1 day"):
        contract.create_task("T", "spec", str(create_address("agent")), 0)

    tid = _create_task(contract, direct_vm, creator)
    assert contract.get_task(tid)["status"] == "open"
    assert contract.get_task(tid)["agent"] != ""


def test_submit_only_agent(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/agent_task_verifier.py")
    creator = create_address("creator")
    other = create_address("other")
    agent = create_address("agent")

    tid = _create_task(contract, direct_vm, creator, str(agent))
    direct_vm.sender = other
    with direct_vm.expect_revert("Only assigned agent can submit"):
        contract.submit_deliverable(tid, DELIVERABLE_URL, DELIVERABLE_DESC)


def test_verify_only_creator(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/agent_task_verifier.py")
    creator = create_address("creator")
    agent = create_address("agent")
    other = create_address("other")

    tid = _create_task(contract, direct_vm, creator, str(agent))
    direct_vm.sender = agent
    contract.submit_deliverable(tid, DELIVERABLE_URL, DELIVERABLE_DESC)

    direct_vm.mock_web(re.escape(DELIVERABLE_URL), {"status": 200, "body": "API docs"})
    direct_vm.mock_llm(re.escape("agent task verifier"), PASS_JSON)
    direct_vm.sender = other
    with direct_vm.expect_revert("Only creator can verify"):
        contract.verify_deliverable(tid)


def test_submit_and_verify_pass(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/agent_task_verifier.py")
    creator = create_address("creator")
    agent = create_address("agent")

    tid = _create_task(contract, direct_vm, creator, str(agent))
    direct_vm.sender = agent
    contract.submit_deliverable(tid, DELIVERABLE_URL, DELIVERABLE_DESC)
    assert contract.get_task(tid)["status"] == "submitted"

    direct_vm.mock_web(re.escape(DELIVERABLE_URL), {"status": 200, "body": "API docs content"})
    direct_vm.mock_llm(re.escape("agent task verifier"), PASS_JSON)
    direct_vm.sender = creator
    result = contract.verify_deliverable(tid)
    assert result["decision"] == "pass"
    assert contract.get_task(tid)["status"] == "verified"
    rep = contract.get_agent_reputation(str(agent))
    assert rep["reputation_score"] == 55
    assert rep["total_tasks"] == 1
    assert rep["passed_tasks"] == 1


def test_verify_fail_reduces_reputation(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/agent_task_verifier.py")
    creator = create_address("creator")
    agent = create_address("agent")

    tid = _create_task(contract, direct_vm, creator, str(agent))
    direct_vm.sender = agent
    contract.submit_deliverable(tid, DELIVERABLE_URL, DELIVERABLE_DESC)

    direct_vm.mock_web(re.escape(DELIVERABLE_URL), {"status": 200, "body": "Incomplete docs"})
    direct_vm.mock_llm(re.escape("agent task verifier"), FAIL_JSON)
    direct_vm.sender = creator
    result = contract.verify_deliverable(tid)
    assert result["decision"] == "fail"
    rep = contract.get_agent_reputation(str(agent))
    assert rep["reputation_score"] == 40
    assert rep["total_tasks"] == 1
    assert rep["passed_tasks"] == 0


def test_views(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/agent_task_verifier.py")
    creator = create_address("creator")
    agent = create_address("agent")

    tid = _create_task(contract, direct_vm, creator, str(agent))
    task = contract.get_task(tid)
    assert task["title"] == TASK_TITLE
    assert task["status"] == "open"
    assert task["verification_deadline"] == ""

    agent_tasks = contract.get_agent_tasks(str(agent))
    assert len(agent_tasks) == 1

    rep = contract.get_agent_reputation(str(agent))
    assert rep["reputation_score"] == 50
    assert rep["total_tasks"] == 0

    assert len(contract.get_all_tasks()) == 1


def test_verify_prompt_binds_fetched_content(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/agent_task_verifier.py")
    creator = create_address("creator")
    agent = create_address("agent")

    tid = _create_task(contract, direct_vm, creator, str(agent))
    direct_vm.sender = agent
    contract.submit_deliverable(tid, DELIVERABLE_URL, DELIVERABLE_DESC)

    body = "Fetched deliverable markdown. AGFETCH_MARKER"
    direct_vm.mock_web(re.escape(DELIVERABLE_URL), {"status": 200, "body": body})
    # Mock matches only if the contract-fetched body is embedded in the prompt.
    direct_vm.mock_llm(
        r"--- BEGIN FETCHED CONTENT ---\s*" + re.escape(body), PASS_JSON
    )
    direct_vm.sender = creator
    result = contract.verify_deliverable(tid)
    assert result["decision"] == "pass"


def test_reputation_is_cumulative_across_tasks(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/agent_task_verifier.py")
    creator = create_address("creator")
    agent = create_address("agent")

    tid1 = _create_task(contract, direct_vm, creator, str(agent))
    direct_vm.sender = agent
    contract.submit_deliverable(tid1, DELIVERABLE_URL, DELIVERABLE_DESC)
    direct_vm.mock_web(re.escape(DELIVERABLE_URL), {"status": 200, "body": "API docs"})
    direct_vm.mock_llm(re.escape("agent task verifier"), PASS_JSON)
    direct_vm.sender = creator
    contract.verify_deliverable(tid1)

    rep = contract.get_agent_reputation(str(agent))
    assert rep["reputation_score"] == 55
    assert rep["total_tasks"] == 1
    assert rep["passed_tasks"] == 1

    direct_vm.clear_mocks()

    tid2 = _create_task(contract, direct_vm, creator, str(agent))
    rep = contract.get_agent_reputation(str(agent))
    assert rep["reputation_score"] == 55, "create_task must not reset the record"
    assert rep["total_tasks"] == 1

    direct_vm.sender = agent
    contract.submit_deliverable(tid2, DELIVERABLE_URL, DELIVERABLE_DESC)
    direct_vm.mock_web(re.escape(DELIVERABLE_URL), {"status": 200, "body": "Partial"})
    direct_vm.mock_llm(re.escape("agent task verifier"), FAIL_JSON)
    direct_vm.sender = creator
    contract.verify_deliverable(tid2)

    rep = contract.get_agent_reputation(str(agent))
    assert rep["reputation_score"] == 45, "prior result must not be lost"
    assert rep["total_tasks"] == 2
    assert rep["passed_tasks"] == 1


def test_timeout_updates_cumulative_record(direct_vm, direct_deploy):
    from datetime import datetime, timedelta

    contract = direct_deploy("contracts/agent_task_verifier.py")
    creator = create_address("creator")
    agent = create_address("agent")

    tid = _create_task(contract, direct_vm, creator, str(agent))
    direct_vm.sender = agent
    contract.submit_deliverable(tid, DELIVERABLE_URL, DELIVERABLE_DESC)

    direct_vm.warp((datetime.now() + timedelta(days=8)).isoformat())
    contract.claim_verification_timeout(tid)

    t = contract.get_task(tid)
    assert t["status"] == "auto_passed"
    rep = contract.get_agent_reputation(str(agent))
    assert rep["reputation_score"] == 55
    assert rep["total_tasks"] == 1
    assert rep["passed_tasks"] == 1
