import { useEffect, useState } from 'react';
import type { ProjectSummary } from '../../../packages/schema/persistence';
import { listProjects } from './projectFiles';
export function ProjectMenu(p: {
  name: string;
  revision: number;
  dirty: boolean;
  busy: boolean;
  rename: (name: string) => void;
  save: () => void;
  create: () => void;
  open: (id: string) => void;
}) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    void attempt;
    void p.revision;
    let current = true;
    setLoading(true);
    setError('');
    void listProjects()
      .then((result) => {
        if (current) setProjects(result.projects);
      })
      .catch((failure) => {
        if (current)
          setError(
            failure instanceof Error
              ? failure.message
              : 'Could not list projects.',
          );
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [attempt, p.revision]);
  return (
    <div className="project-file">
      <label>
        Project name
        <input
          value={p.name}
          disabled={p.busy}
          onChange={(e) => p.rename(e.target.value)}
        />
      </label>
      <p data-testid="save-status">
        {p.dirty
          ? 'Unsaved changes'
          : p.revision
            ? `Saved · revision ${p.revision}`
            : 'Not saved'}
      </p>
      <button
        type="button"
        disabled={p.busy || !p.name.trim() || (!p.dirty && p.revision > 0)}
        onClick={p.save}
      >
        Save project
      </button>
      <button type="button" disabled={p.busy} onClick={p.create}>
        New project
      </button>
      <h3>Open saved project</h3>
      {loading ? (
        <p>Loading projects…</p>
      ) : projects.length ? (
        <ul className="project-list">
          {projects.map((project) => (
            <li key={project.projectId}>
              <button
                type="button"
                disabled={p.busy}
                onClick={() => p.open(project.projectId)}
              >
                {project.name} · revision {project.revision}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        !error && <p>No saved projects.</p>
      )}
      {error && <p role="alert">{error}</p>}
      <button
        type="button"
        disabled={loading || p.busy}
        onClick={() => setAttempt((value) => value + 1)}
      >
        Refresh project list
      </button>
      <p>
        Saved on this computer. Save applied edits before closing; field drafts
        and undo history are not saved.
      </p>
    </div>
  );
}
