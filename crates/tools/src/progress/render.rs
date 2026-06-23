mod cli;

use std::time::Duration;

pub(crate) use cli::CLIRenderer;

pub(crate) trait Renderer {
    fn render(&self, count: usize, total: usize, elapsed: Duration, remaining: Duration);
    fn terminate(&self, count: usize);
}

const SECOND: Duration = Duration::from_secs(1);
const MINUTE: Duration = Duration::from_mins(1);
const HOUR: Duration = Duration::from_hours(1);

fn format_duration(duration: Duration) -> String {
    if duration < SECOND {
        "0s".to_owned()
    } else if duration < MINUTE {
        format!("{}s", duration.as_secs())
    } else if duration < HOUR {
        let secs = duration.as_secs();
        let mins = secs / 60;
        format!("{:02}:{:02}", mins, secs - mins * 60)
    } else {
        let secs = duration.as_secs();
        let hours = secs / 3600;
        let mins = (secs - hours * 3600) / 60;
        format!(
            "{:02}:{:02}:{:02}",
            hours,
            mins,
            secs - hours * 3600 - mins * 60
        )
    }
}
