"""Private per-rule access-policy edits retaining complete request-matrix checks."""

from .scenarios import Security


class SecurityIncremental(Security):
    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        self.tools["patch"]["policy_rule"] = (
            "params={index:integer,rule:{role,kind,method,effect,own_team?,active?,write_approved?,device_trusted?,clearance_ok?}}; replace an existing index or append at the current rule count; first matching rule wins"
        )
        self.instruction += " Prefer short incremental policy_rule edits when building a policy. Replace index 0 to remove the overbroad initial allow rule, then append clauses in their intended order. Inspect policy to audit the result and replay requests before committing."

    def patch(self, target, params):
        if target != "policy_rule":
            return super().patch(target, params)
        if set(params) != {"index", "rule"} or type(params["index"]) is not int:
            raise ValueError("Provide a rule and integer policy index")
        rows = list(self.resources["policy"])
        index = params["index"]
        if not 0 <= index <= len(rows):
            raise ValueError(
                "Replace an existing index or append at current rule count"
            )
        if index == len(rows):
            rows.append(params["rule"])
        else:
            rows[index] = params["rule"]
        super().patch("policy", {"rules": rows})
        return {
            "index": index,
            "rule": dict(rows[index]),
            "rule_count": len(rows),
            "version": self.version,
        }
