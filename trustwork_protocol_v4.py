# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# ============================================================
#  TrustWork Protocol — v4.0
#  AI-Powered Freelance Escrow & Dispute Resolution
#  Built on GenLayer Intelligent Contracts
#  v4 fix: all timestamp references removed
# ============================================================

from genlayer import *
from dataclasses import dataclass


@allow_storage
@dataclass
class Job:
    job_id:           str
    client:           Address
    freelancer:       Address
    title:            str
    brief:            str
    payment_wei:      u256
    deadline:         u256
    status:           str
    deliverable_url:  str
    deliverable_note: str
    ai_verdict:       str
    ai_score:         u256


class TrustWorkProtocol(gl.Contract):

    jobs:             TreeMap[str, Job]
    job_counter:      u256
    platform_fee_bps: u256
    owner:            Address
    total_volume:     u256

    def __init__(self, platform_fee_bps: u256):
        self.jobs             = TreeMap()
        self.job_counter      = u256(0)
        self.platform_fee_bps = platform_fee_bps
        self.owner            = gl.message.sender_address
        self.total_volume     = u256(0)

    @gl.public.write.payable
    def post_job(self, title: str, brief: str, deadline: u256) -> str:
        assert gl.message.value > u256(0), "Must send payment"
        assert len(brief.strip()) >= 20,   "Brief too short (min 20 chars)"
        assert len(title.strip()) >= 3,    "Title too short (min 3 chars)"

        self.job_counter = self.job_counter + u256(1)
        job_id = "TW-" + str(int(self.job_counter))
        null_addr = Address("0x0000000000000000000000000000000000000000")

        self.jobs[job_id] = Job(
            job_id           = job_id,
            client           = gl.message.sender_address,
            freelancer       = null_addr,
            title            = title,
            brief            = brief,
            payment_wei      = gl.message.value,
            deadline         = deadline,
            status           = "OPEN",
            deliverable_url  = "",
            deliverable_note = "",
            ai_verdict       = "",
            ai_score         = u256(0),
        )
        return job_id

    @gl.public.write
    def cancel_job(self, job_id: str):
        job = self.jobs[job_id]
        assert gl.message.sender_address == job.client, "Only client can cancel"
        assert job.status == "OPEN",                    "Can only cancel OPEN jobs"
        assert job.payment_wei > u256(0),               "No funds to refund"
        job.status = "CANCELLED"
        self.jobs[job_id] = job
        job.client.transfer(job.payment_wei)

    @gl.public.write
    def accept_job(self, job_id: str):
        job = self.jobs[job_id]
        assert job.status == "OPEN",                        "Job not open"
        assert gl.message.sender_address != job.client,     "Client cannot self-hire"
        job.freelancer = gl.message.sender_address
        job.status     = "IN_PROGRESS"
        self.jobs[job_id] = job

    @gl.public.write
    def submit_work(self, job_id: str, deliverable_url: str, deliverable_note: str):
        job = self.jobs[job_id]
        assert gl.message.sender_address == job.freelancer, "Only assigned freelancer"
        assert job.status == "IN_PROGRESS",                 "Job must be IN_PROGRESS"
        assert len(deliverable_url.strip()) > 0,            "Provide a deliverable URL"
        assert len(deliverable_note.strip()) >= 20,         "Describe your work (min 20 chars)"
        job.deliverable_url  = deliverable_url
        job.deliverable_note = deliverable_note
        job.status           = "SUBMITTED"
        self.jobs[job_id]    = job

    @gl.public.write
    def evaluate_submission(self, job_id: str):
        job = self.jobs[job_id]
        assert job.status == "SUBMITTED", "Work must be SUBMITTED first"
        assert (
            gl.message.sender_address == job.client or
            gl.message.sender_address == job.freelancer
        ), "Only job participants can trigger evaluation"

        title            = job.title
        brief            = job.brief
        deliverable_url  = job.deliverable_url
        deliverable_note = job.deliverable_note

        prompt = f"""
You are an impartial expert judge evaluating whether a freelancer
has satisfactorily completed a job.

JOB TITLE: {title}

ORIGINAL BRIEF: {brief}

DELIVERABLE URL: {deliverable_url}
FREELANCER EXPLANATION: {deliverable_note}

Respond ONLY with a valid JSON object, no markdown, no extra text:
{{
  "verdict": "APPROVED",
  "score": 85,
  "reasoning": "2-3 sentence explanation.",
  "missing": "Nothing"
}}

Rules:
- APPROVED = score 80-100 (meets brief well)
- PARTIAL  = score 40-79  (partial delivery)
- REJECTED = score 0-39   (does not meet brief)
"""

        def leader_fn():
            result = gl.nondet.exec_prompt(prompt, response_format='json')
            if not isinstance(result, dict):
                raise gl.UserError("LLM returned non-dict")
            return result

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            data = leader_result.calldata
            if not isinstance(data, dict):
                return False
            return (
                data.get("verdict") in ("APPROVED", "PARTIAL", "REJECTED")
                and isinstance(data.get("score"), (int, float))
                and 0 <= float(data.get("score", -1)) <= 100
                and isinstance(data.get("reasoning"), str)
                and len(data.get("reasoning", "")) > 5
            )

        ai_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        if not isinstance(ai_result, dict):
            raise gl.UserError("Invalid AI result format")

        verdict   = ai_result.get("verdict", "REJECTED")
        score     = int(round(float(ai_result.get("score", 0))))
        reasoning = ai_result.get("reasoning", "No reasoning provided.")
        missing   = ai_result.get("missing", "-")

        job.ai_verdict = verdict + " (" + str(score) + "/100) | " + reasoning
        job.ai_score   = u256(score)

        if verdict == "APPROVED":
            job.status = "APPROVED"
            self.jobs[job_id] = job
            self._release_full(job)
        elif verdict == "PARTIAL":
            job.status = "PARTIAL"
            self.jobs[job_id] = job
            self._release_partial(job, score)
        else:
            job.status = "REFUNDED"
            self.jobs[job_id] = job
            job.client.transfer(job.payment_wei)

    @gl.public.write
    def appeal_verdict(self, job_id: str, appeal_reason: str):
        job = self.jobs[job_id]
        assert job.status in ("PARTIAL", "APPROVED"), "Can only appeal PARTIAL or APPROVED"
        assert (
            gl.message.sender_address == job.client or
            gl.message.sender_address == job.freelancer
        ), "Only job participants can appeal"
        assert len(appeal_reason.strip()) >= 30, "Provide detailed reason (min 30 chars)"

        title            = job.title
        brief            = job.brief
        deliverable_url  = job.deliverable_url
        deliverable_note = job.deliverable_note
        prev_verdict     = job.ai_verdict

        appeal_prompt = f"""
You are a senior arbitrator reviewing an appeal.

JOB TITLE: {title}
BRIEF: {brief}
DELIVERABLE: {deliverable_url}
FREELANCER NOTE: {deliverable_note}
PREVIOUS VERDICT: {prev_verdict}
APPEAL REASON: {appeal_reason}

Give a FINAL ruling. Respond ONLY with valid JSON, no markdown:
{{
  "verdict": "APPROVED",
  "score": 85,
  "reasoning": "3-4 sentences acknowledging the appeal.",
  "missing": "Nothing"
}}

APPROVED=80-100, PARTIAL=40-79, REJECTED=0-39.
"""

        def leader_fn():
            result = gl.nondet.exec_prompt(appeal_prompt, response_format='json')
            if not isinstance(result, dict):
                raise gl.UserError("LLM returned non-dict")
            return result

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            data = leader_result.calldata
            return (
                isinstance(data, dict)
                and data.get("verdict") in ("APPROVED", "PARTIAL", "REJECTED")
                and isinstance(data.get("score"), (int, float))
                and 0 <= float(data.get("score", -1)) <= 100
            )

        ai_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        if not isinstance(ai_result, dict):
            raise gl.UserError("Invalid AI result format")

        verdict   = ai_result.get("verdict", "REJECTED")
        score     = int(round(float(ai_result.get("score", 0))))
        reasoning = ai_result.get("reasoning", "")

        job.ai_verdict = "[APPEAL] " + verdict + " (" + str(score) + "/100) | " + reasoning
        job.ai_score   = u256(score)

        if verdict == "APPROVED":
            job.status = "APPROVED"
            self.jobs[job_id] = job
            self._release_full(job)
        elif verdict == "PARTIAL":
            job.status = "PARTIAL"
            self.jobs[job_id] = job
            self._release_partial(job, score)
        else:
            job.status = "REFUNDED"
            self.jobs[job_id] = job
            job.client.transfer(job.payment_wei)

    def _release_full(self, job: Job):
        assert job.payment_wei > u256(0), "No funds to release"
        fee    = (job.payment_wei * self.platform_fee_bps) // u256(10000)
        payout = job.payment_wei - fee
        self.total_volume = self.total_volume + job.payment_wei
        job.freelancer.transfer(payout)
        if fee > u256(0):
            self.owner.transfer(fee)

    def _release_partial(self, job: Job, score: int):
        assert job.payment_wei > u256(0), "No funds to release"
        freelancer_share  = (job.payment_wei * u256(score)) // u256(100)
        client_refund     = job.payment_wei - freelancer_share
        fee               = (freelancer_share * self.platform_fee_bps) // u256(10000)
        freelancer_payout = freelancer_share - fee
        self.total_volume = self.total_volume + job.payment_wei
        if freelancer_payout > u256(0):
            job.freelancer.transfer(freelancer_payout)
        if client_refund > u256(0):
            job.client.transfer(client_refund)
        if fee > u256(0):
            self.owner.transfer(fee)

    @gl.public.view
    def get_job(self, job_id: str) -> Job:
        return self.jobs[job_id]

    @gl.public.view
    def get_job_status(self, job_id: str) -> str:
        return self.jobs[job_id].status

    @gl.public.view
    def get_ai_verdict(self, job_id: str) -> str:
        return self.jobs[job_id].ai_verdict

    @gl.public.view
    def get_total_jobs(self) -> u256:
        return self.job_counter

    @gl.public.view
    def get_total_volume(self) -> u256:
        return self.total_volume

    @gl.public.write
    def update_platform_fee(self, new_fee_bps: u256):
        assert gl.message.sender_address == self.owner, "Only owner"
        assert new_fee_bps <= u256(500),                "Fee cannot exceed 5%"
        self.platform_fee_bps = new_fee_bps
