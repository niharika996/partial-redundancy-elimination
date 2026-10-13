"""
Automated Test Suite for Partial Redundancy Elimination (PRE) Framework.
Tests IR, Parser, CFG, BitVectors, and LCM optimization passes.
"""

import unittest
from src.parser import parse_tac
from src.cfg import build_cfg
from src.ir import Expression
from src.dataflow import BitVector
from src.lcm import LCMFramework
from src.transform import LCMTransformer


class TestPREFramework(unittest.TestCase):

    def test_bitvector_operations(self):
        universe = [Expression("+", "a", "b"), Expression("*", "x", "y"), Expression("-", "m", "n")]
        v1 = BitVector.from_set(universe, {universe[0], universe[1]})
        v2 = BitVector.from_set(universe, {universe[1], universe[2]})

        # Intersection
        self.assertEqual((v1 & v2).to_set(), {universe[1]})
        # Union
        self.assertEqual((v1 | v2).to_set(), {universe[0], universe[1], universe[2]})
        # Difference
        self.assertEqual((v1 - v2).to_set(), {universe[0]})
        # Inversion
        self.assertEqual((~v1).to_set(), {universe[2]})

    def test_parser_and_cfg_leaders(self):
        code = """
        x = a + b
        if x > 10 goto L1
        y = 20
        goto L2
        L1:
        y = 30
        L2:
        return y
        """
        insts = parse_tac(code)
        self.assertEqual(len(insts), 8)
        cfg = build_cfg(insts)
        # Should have 4 user blocks + ENTRY + EXIT
        self.assertEqual(len(cfg.blocks), 4)
        self.assertEqual(cfg.blocks[0].name, "B1")

    def test_classic_pre_pass(self):
        code = """
        if cond > 0 goto L_THEN
        x = a + b
        goto L_MERGE
        L_THEN:
        c = 10
        goto L_MERGE
        L_MERGE:
        y = a + b
        return y
        """
        insts = parse_tac(code)
        cfg = build_cfg(insts)
        cfg.split_critical_edges()
        lcm = LCMFramework(cfg)
        lcm.run_all_passes()
        transformer = LCMTransformer(lcm)
        records = transformer.transform()

        # Check that computations were inserted and replaced
        total_inserted = sum(len(r.inserted) for r in records.values())
        total_replaced = sum(len(r.replaced) for r in records.values())
        self.assertGreater(total_inserted, 0)
        self.assertGreater(total_replaced, 0)

        # Confirm that a + b was inserted into B3 (THEN branch)
        b3_rec = records.get("B3")
        self.assertIsNotNone(b3_rec)
        self.assertTrue(any("t_a_add_b = a + b" in ins for ins in b3_rec.inserted))

        # Confirm that a + b was eliminated from B4 (MERGE block)
        b4_rec = records.get("B4")
        self.assertIsNotNone(b4_rec)
        self.assertTrue(any("y = t_a_add_b" in mod for _, mod in b4_rec.replaced))

    def test_cse_full_redundancy(self):
        code = """
        t1 = x * y
        if val > 5 goto L_PATH1
        a = 1
        goto L_JOIN
        L_PATH1:
        b = 2
        goto L_JOIN
        L_JOIN:
        t2 = x * y
        return t2
        """
        insts = parse_tac(code)
        cfg = build_cfg(insts)
        cfg.split_critical_edges()
        lcm = LCMFramework(cfg)
        lcm.run_all_passes()
        transformer = LCMTransformer(lcm)
        records = transformer.transform()

        # In B4 (L_JOIN), t2 = x * y must be replaced with temporary
        b4_rec = records.get("B4")
        self.assertTrue(any("t2 = t_x_mul_y" in mod for _, mod in b4_rec.replaced))

    def test_licm_loop_hoisting(self):
        code = """
        i = 0
        n = 100
        L_LOOP:
        val = base * factor
        i = i + 1
        if i < n goto L_LOOP
        return val
        """
        insts = parse_tac(code)
        cfg = build_cfg(insts)
        cfg.split_critical_edges()
        lcm = LCMFramework(cfg)
        lcm.run_all_passes()
        transformer = LCMTransformer(lcm)
        records = transformer.transform()

        # In B1 (Pre-header), base * factor must be inserted
        b1_rec = records.get("B1")
        self.assertTrue(any("t_base_mul_factor = base * factor" in ins for ins in b1_rec.inserted))

        # In B2 (Loop body), val = base * factor must be replaced
        b2_rec = records.get("B2")
        self.assertTrue(any("val = t_base_mul_factor" in mod for _, mod in b2_rec.replaced))


if __name__ == "__main__":
    unittest.main()
