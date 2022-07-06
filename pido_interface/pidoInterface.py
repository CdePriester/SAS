from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sas.core.discipline import Discipline


from abc import ABC, abstractmethod


class PIDOInterface(ABC):
    """Abstract Base Class for PIDO interfaces. Actual implementations should be inherited from here"""

    @abstractmethod
    def test_pido_connection(self):
        pass

    @abstractmethod
    def execute_workflow(self, cmdows_file: str,  input_cpacs=None, run_output_folder=None):
        pass

    @abstractmethod
    def process_results(self, database, disciplines, final_storage_base_folder=None, run_id=None):
        pass

    @abstractmethod
    def get_timeline(self, database, disciplines: list[Discipline], run_id):
        pass

    @abstractmethod
    def get_final_cpacs(self, run_id: str, database):
        pass

    @property
    @abstractmethod
    def last_run_file(self):
        pass

    @abstractmethod
    def deploy_custom_design_table_into_workflow(self, wf_file, samples):
        pass

    @abstractmethod
    def set_pido_output(self, location: str):
        pass

    @abstractmethod
    def update_tool_output_location(self, tool_id: str):
        pass

    @abstractmethod
    def deploy_discipline_surrogate(self, surrogate, pickle_file, base_location):
        pass

    @abstractmethod
    def deploy_discipline(self, discipline: Discipline, tool_folder: str, **kwargs):
        pass

    @abstractmethod
    def check_tool_naming_consistency(self, tool_ids):
        pass