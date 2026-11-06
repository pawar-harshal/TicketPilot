import { Spin } from "antd";
import SCENARIOS from "../../data/scenarios";
import ISSUE_ICONS, { ChevronRightIcon } from "../IssueIcons/IssueIcons";
import styles from "./ScenarioPicker.module.css";

/**
 * Issue-category list, rendered inside the "Get Help" drawer (see
 * SubmitTicket.jsx) -- a vertical list of real rows (icon, title,
 * subtitle, chevron), the way an actual delivery app's help center
 * presents issue types, rather than an emoji card grid. Clicking a row
 * immediately submits that scenario's opening message behind the scenes
 * and drops the viewer straight into the chat, already mid-conversation
 * -- like tapping a quick-reply chip in a real support app.
 */
function ScenarioPicker({ onPick, loadingId }) {
  return (
    <div className={styles.list}>
      {SCENARIOS.map((scenario) => {
        const isLoading = loadingId === scenario.id;
        const Icon = ISSUE_ICONS[scenario.icon] || ISSUE_ICONS.help;
        return (
          <div
            key={scenario.id}
            className={styles.row}
            role="button"
            tabIndex={0}
            onClick={() => !loadingId && onPick(scenario)}
            onKeyDown={(e) => {
              if ((e.key === "Enter" || e.key === " ") && !loadingId) onPick(scenario);
            }}
          >
            <div className={styles.icon}>
              <Icon />
            </div>
            <div className={styles.body}>
              <span className={styles.title}>{scenario.title}</span>
              <div className={styles.subtitle}>{scenario.subtitle}</div>
            </div>
            <ChevronRightIcon className={styles.chevron} />
            {isLoading && (
              <div className={styles.overlay}>
                <Spin size="small" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default ScenarioPicker;
