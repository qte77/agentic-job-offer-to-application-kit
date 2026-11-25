### Changed

- Tailor workflow: the CV and cover letter always use the same contact placeholders, `[Your Name]`, `[email]`, `[phone]` and `[city, country]`. The prefill pack's name, email and phone fields are always `[NEEDS HUMAN INPUT]`. No doc carries a real or guessed name, email or phone from any context, or a username as the name. Portfolio links from the evidence library stay.
- Tailor workflow: every prefill pack opens with an `Apply via:` line naming where to submit: the route the JD states (careers portal or ATS, email address, job board), else the posting URL.
- Tailor workflow: every agent is told to ignore any chat message it can see. Tailor subagents had answered the owner's chat questions inside the match, gap report and prefill files.
- Tailor workflow: a CV returned double-encoded as JSON (`{"cv": "..."}`) is unwrapped, and a CV that comes back as a stub (under 800 characters, such as `{"placeholder": "see below"}`) is asked for once more. A second stub fails the run instead of saving an empty CV.
