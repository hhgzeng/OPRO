import pytest
from opro.optimization import opt_utils


def test_gen_ins_and_score_pairs_substr_order():
    history = [
        ("ins_low", 0.2, 0),
        ("ins_mid", 0.5, 1),
        ("ins_high", 0.9, 2),
    ]

    # Ascending (default)
    s_asc = opt_utils.gen_ins_and_score_pairs_substr(
        history, instruction_order="ascending", return_str_only=True
    )
    assert s_asc.find("ins_low") < s_asc.find("ins_mid") < s_asc.find("ins_high")

    # Descending
    s_desc = opt_utils.gen_ins_and_score_pairs_substr(
        history, instruction_order="descending", return_str_only=True
    )
    assert s_desc.find("ins_high") < s_desc.find("ins_mid") < s_desc.find("ins_low")


def test_gen_ins_and_score_pairs_substr_scores():
    history = [("ins_1", 0.75, 0)]
    s_with = opt_utils.gen_ins_and_score_pairs_substr(
        history, show_scores=True, return_str_only=True
    )
    assert "score:" in s_with
    assert "0.75" in s_with

    s_without = opt_utils.gen_ins_and_score_pairs_substr(
        history, show_scores=False, return_str_only=True
    )
    assert "score:" not in s_without
    assert "ins_1" in s_without


def test_gen_meta_prompt_ablation():
    history = [("ins_1", 0.5, 0), ("ins_2", 0.8, 1)]
    mp = opt_utils.gen_meta_prompt(
        old_instructions_and_scores=history,
        instruction_pos="Q_begin",
        optimizer_llm_name="gpt-3.5-turbo",
        dataset_name="bbh",
        task_name="movie_recommendation",
        few_shot_qa_pairs=False,
        show_scores=False,
    )
    assert "Below are some previous instructions.\n" in mp
    assert "score:" not in mp
