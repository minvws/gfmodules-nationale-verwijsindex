import unittest

from app.data import DataDomain, Pseudonym, UraNumber


class TestDataDomain(unittest.TestCase):
    def test_careplan(self) -> None:
        self.assertEqual("zorgplan", str(DataDomain.CarePlan))
        self.assertEqual(DataDomain.CarePlan, DataDomain.from_fhir("CarePlan"))
        self.assertEqual("CarePlan", DataDomain.CarePlan.to_fhir())


class TestPseudonym(unittest.TestCase):
    def test_pseudonym(self) -> None:
        self.assertEqual(
            "79079133-8513-4ced-a21e-b7a41f0cf348",
            str(Pseudonym("79079133-8513-4ced-a21e-b7a41f0cf348")),
        )
        self.assertEqual(
            "ea0b4ecf-8d46-4798-80a5-33252db21f1a",
            str(Pseudonym("ea0b4ecf-8d46-4798-80a5-33252db21f1a")),
        )
        self.assertEqual(
            "ea0b4ecf-8d46-4798-80a5-33252db21f1a",
            str(Pseudonym("ea0b4ecf8d46479880a533252db21f1a")),
        )

        with self.assertRaises(ValueError):
            Pseudonym("124")
        with self.assertRaises(ValueError):
            Pseudonym("foobar")
        with self.assertRaises(ValueError):
            Pseudonym("")


class TestUraNumber(unittest.TestCase):
    def test_ura_number(self) -> None:
        self.assertEqual("00001234", str(UraNumber("1234")))
        self.assertEqual("12345678", str(UraNumber("12345678")))

        with self.assertRaises(ValueError):
            UraNumber("1234567890")
        with self.assertRaises(ValueError):
            UraNumber("foobar")
        with self.assertRaises(ValueError):
            UraNumber("1A525")
        with self.assertRaises(ValueError):
            UraNumber("")
