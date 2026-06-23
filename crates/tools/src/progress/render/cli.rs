use std::time::Duration;

use crate::progress::render::{Renderer, format_duration};

pub(crate) struct CLIRenderer {
    len: usize,
}

impl CLIRenderer {
    const CLEAR: &'static str = "\x1b[0G\x1b[0J";

    pub fn new() -> Self {
        Self {
            len: (termsize::get()
                .unwrap_or(termsize::Size { rows: 0, cols: 10 })
                .cols) as usize,
        }
    }

    fn print(&self, msg: &str) {
        let clear = CLIRenderer::CLEAR;
        eprint!("{clear}");

        eprint!("{msg}");
    }
}

impl Renderer for CLIRenderer {
    fn render(&self, count: usize, total: usize, elapsed: Duration, remaining: Duration) {
        let bar;
        let text;

        match (count, total) {
            (0, 0) => {
                text = format!(
                    "0/0 {} - eta {}",
                    format_duration(elapsed),
                    format_duration(remaining)
                );

                let len = self.len - 3 - text.len();
                let bar_content = " ??".repeat(len.div_ceil(3))[..len].to_string();
                bar = format!("[{bar_content}]");
            }
            (_, 0) => {
                text = format!(
                    "{count}/0 {} - eta {}",
                    format_duration(elapsed),
                    format_duration(remaining)
                );

                let len = self.len - 3 - text.len();
                bar = format!("[{}]", " ".repeat(len));
            }
            (0, _) => {
                text = format!(
                    "0/{total} {} - eta {}",
                    format_duration(elapsed),
                    format_duration(remaining)
                );

                let len = self.len - 3 - text.len();
                bar = format!("[{}]", " ".repeat(len));
            }
            _ => {
                text = format!(
                    "{count}/{total} {} - eta {}",
                    format_duration(elapsed),
                    format_duration(remaining)
                );

                let len = self.len - 3 - text.len();
                let progress = (count * len).div_ceil(total);
                bar = format!("[{}{}]", "#".repeat(progress), " ".repeat(len - progress));
            }
        }

        self.print(&format!("{bar} {text}"));
    }

    fn terminate(&self, count: usize) {
        self.print(&format!("Done (analyzed {} files)\n", count));
    }
}
