#!/usr/bin/env python3
"""Pruebas unitarias y de simulación de usuario para install_hooks.py.

Valida el ciclo de vida completo de los Git Hooks nativos (pre-commit y pre-push):
instalación, verificación, desinstalación, escaneo determinista de secretos en staging,
y ejecución de gates de pre-commit y pre-push en repositorios temporales aislados.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.install_hooks import (
    FORBIDDEN_FILENAMES,
    MANAGED_MARKER,
    SECRET_PATTERNS,
    check_hooks_installed,
    find_repo_root,
    install_git_hooks,
    is_forbidden_filename,
    main,
    run_pre_commit_checks,
    run_pre_push_checks,
    scan_staged_secrets,
    uninstall_git_hooks,
)


class TestInstallHooksUnit(unittest.TestCase):
    """Pruebas unitarias de funciones puras de detección y ciclo de vida de hooks."""

    def test_is_forbidden_filename(self) -> None:
        """Verifica la detección exacta de archivos de entorno y llaves prohibidas."""
        for forbidden in FORBIDDEN_FILENAMES:
            self.assertTrue(
                is_forbidden_filename(forbidden),
                f"El archivo {forbidden} debería considerarse prohibido.",
            )
            self.assertTrue(
                is_forbidden_filename(f"subfolder/{forbidden}"),
                f"La ruta anidada subfolder/{forbidden} debería considerarse prohibida.",
            )

        # Variantes de .env
        self.assertTrue(is_forbidden_filename(".env.staging"))
        self.assertTrue(is_forbidden_filename(".env.test"))

        # Excepciones válidas de plantillas documentadas
        self.assertFalse(is_forbidden_filename(".env.example"))
        self.assertFalse(is_forbidden_filename(".env.template"))
        self.assertFalse(is_forbidden_filename("config/.env.example"))
        self.assertFalse(is_forbidden_filename("custom.env.example"))

        # Archivos convencionales
        self.assertFalse(is_forbidden_filename("main.py"))
        self.assertFalse(is_forbidden_filename("README.md"))

    def test_secret_patterns_match(self) -> None:
        """Comprueba que los patrones regex identifiquen credenciales y rechacen cadenas inocuas."""
        # Se construyen dinámicamente para no incluir cadenas literales en el propio test
        fake_private_key = "-----BEGIN " + "PRIVATE KEY-----"
        fake_rsa_key = "-----BEGIN " + "RSA KEY-----"
        fake_gh_token = "ghp_" + ("x" * 32)
        fake_sk_token = "sk-" + ("y" * 32)
        fake_google_token = "AIza" + ("z" * 35)

        sample_cases = [
            fake_private_key,
            fake_rsa_key,
            fake_gh_token,
            fake_sk_token,
            fake_google_token,
        ]

        for secret in sample_cases:
            matched = any(pattern.search(secret) for pattern in SECRET_PATTERNS)
            self.assertTrue(matched, f"El patrón debería detectar la credencial simulada: {secret[:10]}...")

        # Texto normal no debe coincidir
        clean_text = "def calculate_total(price: float) -> float:\n    return price * 1.16\n"
        matched_clean = any(pattern.search(clean_text) for pattern in SECRET_PATTERNS)
        self.assertFalse(matched_clean, "El código limpio no debe activar falsos positivos.")

    def test_find_repo_root(self) -> None:
        """Verifica la resolución ascendente de la raíz del repositorio."""
        root = find_repo_root()
        self.assertTrue((root / ".git").exists(), "find_repo_root debe resolver un repositorio con .git.")


class TestInstallHooksLifecycle(unittest.TestCase):
    """Pruebas del ciclo de vida de hooks en repositorios Git temporales."""

    def setUp(self) -> None:
        """Crea un repositorio Git temporal y aislado para cada prueba."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        subprocess.run(["git", "init"], cwd=self.repo_root, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test Subagent"],
            cwd=self.repo_root,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "subagent@test.local"],
            cwd=self.repo_root,
            capture_output=True,
            check=True,
        )

    def tearDown(self) -> None:
        """Limpia el entorno temporal tras finalizar cada prueba."""
        self.temp_dir.cleanup()

    def test_install_check_uninstall_lifecycle(self) -> None:
        """Verifica la secuencia completa de instalación, comprobación y desinstalación."""
        # 1. Inicialmente no hay hooks instalados
        status_initial = check_hooks_installed(self.repo_root)
        self.assertFalse(status_initial["installed"])
        self.assertFalse(status_initial["pre-commit"]["exists"])
        self.assertFalse(status_initial["pre-push"]["exists"])

        # 2. Instalación de hooks
        install_res = install_git_hooks(self.repo_root)
        self.assertTrue(install_res["success"])
        self.assertIn("pre-commit", install_res["installed"])
        self.assertIn("pre-push", install_res["installed"])

        # 3. Comprobación de hooks instalados y gestionados
        status_after_install = check_hooks_installed(self.repo_root)
        self.assertTrue(status_after_install["installed"])
        self.assertTrue(status_after_install["pre-commit"]["exists"])
        self.assertTrue(status_after_install["pre-commit"]["managed"])
        self.assertTrue(status_after_install["pre-push"]["exists"])
        self.assertTrue(status_after_install["pre-push"]["managed"])

        # 4. Verificación del contenido de los scripts
        pre_commit_file = self.repo_root / ".git" / "hooks" / "pre-commit"
        pre_push_file = self.repo_root / ".git" / "hooks" / "pre-push"
        self.assertTrue(pre_commit_file.is_file())
        self.assertTrue(pre_push_file.is_file())

        pre_commit_content = pre_commit_file.read_text(encoding="utf-8")
        pre_push_content = pre_push_file.read_text(encoding="utf-8")
        self.assertIn(MANAGED_MARKER, pre_commit_content)
        self.assertIn(MANAGED_MARKER, pre_push_content)
        self.assertIn("scripts/install_hooks.py --run-pre-commit", pre_commit_content)
        self.assertIn("scripts/install_hooks.py --run-pre-push", pre_push_content)

        # 5. Desinstalación
        uninstall_res = uninstall_git_hooks(self.repo_root)
        self.assertTrue(uninstall_res["success"])
        self.assertIn("pre-commit", uninstall_res["uninstalled"])
        self.assertIn("pre-push", uninstall_res["uninstalled"])

        # 6. Comprobación tras desinstalación
        status_after_uninstall = check_hooks_installed(self.repo_root)
        self.assertFalse(status_after_uninstall["installed"])
        self.assertFalse(status_after_uninstall["pre-commit"]["exists"])
        self.assertFalse(status_after_uninstall["pre-push"]["exists"])

    def test_unmanaged_hook_preservation_and_force_overwrite(self) -> None:
        """Verifica que hooks de terceros sin marca no sean sobreescritos sin --force ni borrados."""
        hooks_dir = self.repo_root / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        custom_hook = hooks_dir / "pre-commit"
        custom_hook.write_text("#!/bin/sh\necho 'custom hook de tercero'\n", encoding="utf-8")

        # Intento de instalación sin force: debe omitirlo
        res_no_force = install_git_hooks(self.repo_root, force=False)
        self.assertTrue(any("pre-commit" in msg for msg in res_no_force["skipped"]))
        self.assertEqual(custom_hook.read_text(encoding="utf-8"), "#!/bin/sh\necho 'custom hook de tercero'\n")

        # Desinstalación no debe eliminar un hook no gestionado
        uninst_res = uninstall_git_hooks(self.repo_root)
        self.assertTrue(custom_hook.is_file())
        self.assertTrue(any("pre-commit" in msg for msg in uninst_res["skipped"]))

        # Con force=True debe sobreescribirlo e insertar la marca
        res_force = install_git_hooks(self.repo_root, force=True)
        self.assertTrue(res_force["success"])
        self.assertIn("pre-commit", res_force["installed"])
        self.assertIn(MANAGED_MARKER, custom_hook.read_text(encoding="utf-8"))


class TestStagedSecretsAndGatesSimulation(unittest.TestCase):
    """Pruebas de simulación de usuario de escaneo de secretos y gates pre-commit / pre-push."""

    def setUp(self) -> None:
        """Prepara el repositorio Git temporal para la prueba."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        subprocess.run(["git", "init"], cwd=self.repo_root, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test Subagent"],
            cwd=self.repo_root,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "subagent@test.local"],
            cwd=self.repo_root,
            capture_output=True,
            check=True,
        )

    def tearDown(self) -> None:
        """Limpia el repositorio temporal."""
        self.temp_dir.cleanup()

    def test_scan_staged_secrets_clean_file(self) -> None:
        """Verifica que un archivo limpio pase sin violaciones."""
        clean_file = self.repo_root / "hello.py"
        clean_file.write_text("print('Hello World')\n", encoding="utf-8")
        subprocess.run(["git", "add", "hello.py"], cwd=self.repo_root, check=True)

        violations = scan_staged_secrets(self.repo_root)
        self.assertEqual(violations, [])

    def test_scan_staged_secrets_forbidden_env_file(self) -> None:
        """Verifica que un archivo .env en staging sea bloqueado categóricamente."""
        env_file = self.repo_root / ".env"
        env_file.write_text("DATABASE_URL=postgres://localhost:5432\n", encoding="utf-8")
        subprocess.run(["git", "add", ".env"], cwd=self.repo_root, check=True)

        violations = scan_staged_secrets(self.repo_root)
        self.assertEqual(len(violations), 1)
        self.assertIn(".env", violations[0])

    def test_scan_staged_secrets_exempt_env_example(self) -> None:
        """Verifica que un archivo .env.example en staging sea permitido."""
        example_file = self.repo_root / ".env.example"
        example_file.write_text("DATABASE_URL=postgres://usuario:clave@host:5432/db\n", encoding="utf-8")
        subprocess.run(["git", "add", ".env.example"], cwd=self.repo_root, check=True)

        violations = scan_staged_secrets(self.repo_root)
        self.assertEqual(violations, [])

    def test_scan_staged_secrets_private_key_pattern(self) -> None:
        """Verifica que un archivo con una llave privada sea detectado por el escáner."""
        secret_file = self.repo_root / "credentials.txt"
        secret_body = "-----BEGIN " + "PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----\n"
        secret_file.write_text(secret_body, encoding="utf-8")
        subprocess.run(["git", "add", "credentials.txt"], cwd=self.repo_root, check=True)

        violations = scan_staged_secrets(self.repo_root)
        self.assertEqual(len(violations), 1)
        self.assertIn("credentials.txt", violations[0])

    def test_run_pre_commit_gate_blocking_and_passing(self) -> None:
        """Verifica la ejecución integral del gate pre-commit."""
        # 1. Caso limpio: debe pasar con éxito
        src_file = self.repo_root / "app.py"
        src_file.write_text("def run(): pass\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=self.repo_root, check=True)

        success, messages = run_pre_commit_checks(self.repo_root)
        self.assertTrue(success)
        self.assertTrue(any("exitosamente" in m for m in messages))

        # 2. Caso bloqueado con secreto: debe fallar
        secret_file = self.repo_root / "config.json"
        fake_token = "ghp_" + ("k" * 32)
        secret_file.write_text(f'{{"github_token": "{fake_token}"}}\n', encoding="utf-8")
        subprocess.run(["git", "add", "config.json"], cwd=self.repo_root, check=True)

        success_fail, messages_fail = run_pre_commit_checks(self.repo_root)
        self.assertFalse(success_fail)
        self.assertTrue(any("config.json" in m for m in messages_fail))

    def test_run_pre_push_gate(self) -> None:
        """Verifica la ejecución del gate pre-push sin drift."""
        success, messages = run_pre_push_checks(self.repo_root)
        self.assertTrue(success)
        self.assertTrue(any("exitosamente" in m for m in messages))

    def test_cli_interface_full_simulation(self) -> None:
        """Simula el flujo completo de comandos invocando main()."""
        # 1. CLI --install
        ret_install = main(["--root", str(self.repo_root), "--install"])
        self.assertEqual(ret_install, 0)

        # 2. CLI --check en formato JSON
        ret_check = main(["--root", str(self.repo_root), "--check", "--json"])
        self.assertEqual(ret_check, 0)

        # 3. CLI --run-pre-commit con staging limpio
        clean_file = self.repo_root / "module.py"
        clean_file.write_text("X = 42\n", encoding="utf-8")
        subprocess.run(["git", "add", "module.py"], cwd=self.repo_root, check=True)

        ret_pre_commit_clean = main(["--root", str(self.repo_root), "--run-pre-commit"])
        self.assertEqual(ret_pre_commit_clean, 0)

        # 4. CLI --run-pre-commit bloqueando .env
        bad_file = self.repo_root / ".env"
        bad_file.write_text("SECRET=123\n", encoding="utf-8")
        subprocess.run(["git", "add", ".env"], cwd=self.repo_root, check=True)

        ret_pre_commit_bad = main(["--root", str(self.repo_root), "--run-pre-commit", "--json"])
        self.assertEqual(ret_pre_commit_bad, 1)

        # 5. CLI --run-pre-push
        ret_pre_push = main(["--root", str(self.repo_root), "--run-pre-push"])
        self.assertEqual(ret_pre_push, 0)

        # 6. CLI --uninstall
        ret_uninstall = main(["--root", str(self.repo_root), "--uninstall"])
        self.assertEqual(ret_uninstall, 0)

        # 7. CLI --check tras desinstalación debe devolver 1
        ret_check_after = main(["--root", str(self.repo_root), "--check"])
        self.assertEqual(ret_check_after, 1)


if __name__ == "__main__":
    unittest.main()
