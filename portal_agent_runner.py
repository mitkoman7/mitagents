"""
Portal Agent Runner - Execute autonomous agents through the web platform
Allows spawning and managing multi-step agent tasks via the Flask interface
"""

import json
import uuid
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

class AgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class AgentTask:
    """Represents a single agent task"""
    task_id: str
    name: str
    description: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    steps: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'result': self.result,
            'error': self.error,
            'steps': self.steps
        }

class AgentRunner:
    """Manages agent execution and lifecycle"""

    def __init__(self, tools: List[Any], llm: Any):
        self.tools = tools
        self.llm = llm
        self.active_tasks: Dict[str, AgentTask] = {}
        self.task_history: List[AgentTask] = []

    def create_task(self, name: str, description: str, user_goal: str) -> str:
        """Create a new agent task"""
        task_id = str(uuid.uuid4())
        task = AgentTask(
            task_id=task_id,
            name=name,
            description=description,
            status=AgentStatus.PENDING.value,
            created_at=datetime.now().isoformat()
        )
        self.active_tasks[task_id] = task
        return task_id

    def get_task(self, task_id: str) -> Optional[AgentTask]:
        """Get task by ID"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        # Check history
        for task in self.task_history:
            if task.task_id == task_id:
                return task
        return None

    def list_tasks(self, status: Optional[str] = None) -> List[AgentTask]:
        """List all tasks, optionally filtered by status"""
        all_tasks = list(self.active_tasks.values()) + self.task_history
        if status:
            return [t for t in all_tasks if t.status == status]
        return all_tasks

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        task = self.get_task(task_id)
        if task and task.status in [AgentStatus.PENDING.value, AgentStatus.RUNNING.value]:
            task.status = AgentStatus.CANCELLED.value
            task.completed_at = datetime.now().isoformat()
            self._archive_task(task_id)
            return True
        return False

    def _archive_task(self, task_id: str):
        """Move task to history"""
        if task_id in self.active_tasks:
            task = self.active_tasks.pop(task_id)
            self.task_history.append(task)
            # Keep only last 100 tasks in history
            if len(self.task_history) > 100:
                self.task_history = self.task_history[-100:]

    def add_step(self, task_id: str, step_name: str, step_description: str, step_result: Any = None):
        """Add a step to task execution"""
        task = self.get_task(task_id)
        if task:
            step = {
                'name': step_name,
                'description': step_description,
                'result': step_result,
                'timestamp': datetime.now().isoformat()
            }
            task.steps.append(step)

class AgentTemplates:
    """Pre-built agent templates for common tasks"""

    @staticmethod
    def data_analysis_agent(query: str, table_name: str = None) -> Dict[str, Any]:
        """Agent that performs data analysis on Databricks"""
        return {
            'name': 'Data Analysis Agent',
            'description': f'Analyze data: {query}',
            'type': 'data_analysis',
            'steps': [
                {'action': 'list_tables', 'description': 'Discover available tables'},
                {'action': 'get_table_schema', 'params': {'table_name': table_name}, 'description': 'Understand data structure'},
                {'action': 'execute_sql', 'params': {'query': query}, 'description': 'Execute analysis query'},
                {'action': 'email_me', 'description': 'Send results via email'}
            ]
        }

    @staticmethod
    def sports_intelligence_agent(team: str, analysis_type: str = 'recent_performance') -> Dict[str, Any]:
        """Agent that analyzes sports team performance"""
        return {
            'name': 'Sports Intelligence Agent',
            'description': f'Analyze {team} - {analysis_type}',
            'type': 'sports_intelligence',
            'steps': [
                {'action': 'get_team_recent_matches', 'params': {'team_name': team}, 'description': f'Get {team} recent matches'},
                {'action': 'get_league_standings', 'description': 'Get league standings for context'},
                {'action': 'email_me', 'description': 'Send analysis report'}
            ]
        }

    @staticmethod
    def location_intelligence_agent(location: str, purpose: str) -> Dict[str, Any]:
        """Agent that provides location intelligence"""
        return {
            'name': 'Location Intelligence Agent',
            'description': f'Location analysis for {location} - {purpose}',
            'type': 'location_intelligence',
            'steps': [
                {'action': 'search_places', 'params': {'query': purpose, 'location': location}, 'description': 'Find relevant places'},
                {'action': 'get_traffic_info', 'params': {'location': location}, 'description': 'Check traffic conditions'},
                {'action': 'nearby_search', 'description': 'Find nearby amenities'},
                {'action': 'email_me', 'description': 'Send location report'}
            ]
        }

    @staticmethod
    def etl_pipeline_agent(notebook_path: str, cluster_id: str = None) -> Dict[str, Any]:
        """Agent that runs ETL pipeline"""
        return {
            'name': 'ETL Pipeline Agent',
            'description': f'Run ETL: {notebook_path}',
            'type': 'etl_pipeline',
            'steps': [
                {'action': 'get_cluster_status', 'params': {'cluster_id': cluster_id}, 'description': 'Check cluster status'},
                {'action': 'start_cluster', 'params': {'cluster_id': cluster_id}, 'condition': 'if_stopped', 'description': 'Start cluster if needed'},
                {'action': 'run_notebook', 'params': {'notebook_path': notebook_path, 'cluster_id': cluster_id}, 'description': 'Execute ETL notebook'},
                {'action': 'get_job_run_status', 'description': 'Monitor execution'},
                {'action': 'email_me', 'description': 'Send completion notification'}
            ]
        }

    @staticmethod
    def multi_service_research_agent(topic: str) -> Dict[str, Any]:
        """Agent that combines multiple services for research"""
        return {
            'name': 'Multi-Service Research Agent',
            'description': f'Research topic: {topic}',
            'type': 'multi_service_research',
            'steps': [
                {'action': 'execute_sql', 'description': 'Query relevant data from Databricks'},
                {'action': 'search_places', 'description': 'Find related locations'},
                {'action': 'get_team_recent_matches', 'condition': 'if_sports_related', 'description': 'Get sports data if applicable'},
                {'action': 'email_me', 'description': 'Send comprehensive report'}
            ]
        }

class AgentExecutor:
    """Executes agent tasks autonomously"""

    def __init__(self, runner: AgentRunner, execute_tool_func):
        self.runner = runner
        self.execute_tool = execute_tool_func

    def execute_task(self, task_id: str, agent_config: Dict[str, Any]) -> bool:
        """Execute an agent task based on configuration"""
        task = self.runner.get_task(task_id)
        if not task:
            return False

        try:
            # Update task status
            task.status = AgentStatus.RUNNING.value
            task.started_at = datetime.now().isoformat()

            # Execute steps
            results = []
            for step in agent_config.get('steps', []):
                action = step.get('action')
                params = step.get('params', {})
                description = step.get('description', action)
                condition = step.get('condition')

                # Check condition if exists
                if condition and not self._check_condition(condition, results):
                    self.runner.add_step(task_id, action, f'Skipped: {description}', None)
                    continue

                # Execute the action
                try:
                    result = self.execute_tool(action, params)
                    results.append({'action': action, 'result': result})
                    self.runner.add_step(task_id, action, description, result)
                except Exception as e:
                    error_msg = f"Step failed: {str(e)}"
                    self.runner.add_step(task_id, action, description, {'error': error_msg})
                    # Continue with other steps

            # Mark as completed
            task.status = AgentStatus.COMPLETED.value
            task.completed_at = datetime.now().isoformat()
            task.result = json.dumps(results, indent=2)

            # Archive the task
            self.runner._archive_task(task_id)
            return True

        except Exception as e:
            task.status = AgentStatus.FAILED.value
            task.completed_at = datetime.now().isoformat()
            task.error = str(e)
            self.runner._archive_task(task_id)
            return False

    def _check_condition(self, condition: str, previous_results: List[Dict]) -> bool:
        """Check if condition is met to execute step"""
        # Simple condition checking - can be extended
        if condition == 'if_stopped':
            # Check if cluster is stopped in previous results
            for result in previous_results:
                if result.get('action') == 'get_cluster_status':
                    result_data = result.get('result', {})
                    if isinstance(result_data, str):
                        result_data = json.loads(result_data)
                    state = result_data.get('state', '')
                    return state in ['TERMINATED', 'STOPPED']
            return False

        if condition == 'if_sports_related':
            # Simple heuristic - check if any sports-related data was found
            return len(previous_results) > 0

        return True

# Pre-defined agent workflows
AGENT_WORKFLOWS = {
    'data_analyst': {
        'name': 'Data Analyst Agent',
        'description': 'Analyzes data from Databricks and provides insights',
        'capabilities': ['SQL queries', 'Data exploration', 'Report generation'],
        'template': AgentTemplates.data_analysis_agent
    },
    'sports_analyst': {
        'name': 'Sports Analyst Agent',
        'description': 'Analyzes team performance and provides sports insights',
        'capabilities': ['Match analysis', 'Team statistics', 'League standings'],
        'template': AgentTemplates.sports_intelligence_agent
    },
    'location_scout': {
        'name': 'Location Scout Agent',
        'description': 'Finds and analyzes locations with traffic and nearby amenities',
        'capabilities': ['Place search', 'Traffic analysis', 'Nearby amenities'],
        'template': AgentTemplates.location_intelligence_agent
    },
    'etl_orchestrator': {
        'name': 'ETL Orchestrator Agent',
        'description': 'Manages and executes ETL pipelines on Databricks',
        'capabilities': ['Cluster management', 'Notebook execution', 'Pipeline monitoring'],
        'template': AgentTemplates.etl_pipeline_agent
    },
    'research_assistant': {
        'name': 'Research Assistant Agent',
        'description': 'Combines multiple data sources for comprehensive research',
        'capabilities': ['Multi-source data', 'Cross-service integration', 'Report compilation'],
        'template': AgentTemplates.multi_service_research_agent
    }
}
