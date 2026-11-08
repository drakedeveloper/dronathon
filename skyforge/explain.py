"""Render deterministic decision evidence; no generated medical diagnosis."""


def explain_decision(decision):
    code=decision['decision_code'];details=decision.get('decision_details',{})
    target=decision.get('target_track_id')
    if code=='HIGHEST_URGENCY_FEASIBLE':
        candidate=next((c for c in details.get('candidates',[]) if c['id']==target),None)
        if candidate:
            return (f"{target}: urgency {candidate['urgency']} from {candidate['urgency_source']}; "
                f"estimated rescue-and-return {candidate['required_energy_wh']:.2f} Wh, "
                f"available {details['available_energy_wh']:.2f} Wh. Urgency ranks before travel time.")
    if code=='DYNAMIC_ENERGY_RETURN':
        return (f"Return reserve reached: available {details.get('available_energy_wh',0):.2f} Wh, "
                f"return threshold {details.get('return_threshold_wh',0):.2f} Wh, including descent and landing.")
    messages={
        'TAKEOFF_TO_SURVEY_ALTITUDE':'Climb vertically to the configured survey altitude before horizontal travel.',
        'INVESTIGATE_DISTRESS_BEACON':'Investigate the highest-urgency unconfirmed radio beacon. Camera confirmation is required before delivery.',
        'SUPPLIES_DELIVERED_RETURN':'All carried supplies delivered. Return to base without spending reserve on further searching.',
        'TEMPORARY_RETURN_ROUTE_BLOCKED_HOLD':'No return route was established within the current constraints and search budget. Hold and replan.',
        'COVERAGE_ROUTE_PENDING_HOLD':'The next search objective remains unvisited; route-search failure does not count as coverage.',
        'SURVEY_COMPLETE_RETURN':'Search objectives exhausted; follow the checked return route.',
        'SAFETY_SHIELD_REJECTED_ROUTE':'Independent shield rejected the proposal: '+', '.join(details.get('shield_violations',[]))+'. Hold for replanning.',
        'SAFETY_SHIELD_RETURN_OVERRIDE':'Independent shield overruled the proposal to protect the return reserve.',
        'EMERGENCY_LOW_ENERGY_LAND':'Return cannot be completed with the remaining energy. Land locally; this is not a successful return.',
        'LANDED':'Landing position reached at base. Independent mission evaluation follows.',
    }
    return messages.get(code,code.replace('_',' ').capitalize()+'.')
