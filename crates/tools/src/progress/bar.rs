use std::time::{Duration, Instant};

use crate::progress::ema::ExpMovingAverage;
use crate::progress::render::Renderer;

pub struct ProgressBar {
    count: usize,
    total: usize,
    min_interval: Duration,
    renderer: Box<dyn Renderer + Send + Sync>,
    last_render_time: Instant,
    last_update_time: Instant,
    start_time: Instant,
    ema: ExpMovingAverage,
}

impl ProgressBar {
    pub fn new(renderer: Box<dyn Renderer + Send + Sync>) -> Self {
        let time = Instant::now();
        Self {
            count: 0,
            total: 0,
            min_interval: Duration::from_millis(100),
            renderer,
            last_render_time: time,
            last_update_time: time,
            start_time: time,
            ema: ExpMovingAverage::new(0.3),
        }
    }

    pub fn has_completed(&self) -> bool {
        self.count == self.total
    }

    pub fn update_count(&mut self) {
        self.count += 1;

        self.ema
            .update(self.last_update_time.elapsed().as_secs_f64());
        self.last_update_time = Instant::now();

        if self.last_render_time.elapsed() >= self.min_interval {
            self.last_render_time = Instant::now();
            // let remaining = (self.total - self.count) as f64 * self.ema.avg();
            let remaining = self.start_time.elapsed().as_secs_f64() / self.count as f64
                * (self.total - self.count) as f64;
            self.renderer.render(
                self.count,
                self.total,
                self.start_time.elapsed(),
                Duration::from_secs(remaining as u64),
            );
        }
    }

    pub fn update_total(&mut self) {
        self.total += 1;

        if self.last_render_time.elapsed() >= self.min_interval {
            self.last_render_time = Instant::now();
            let remaining = (self.total - self.count) as f64 * self.ema.avg();
            self.renderer.render(
                self.count,
                self.total,
                self.start_time.elapsed(),
                Duration::from_secs(remaining as u64),
            );
        }
    }

    pub fn close(&self) {
        self.renderer.terminate(self.count);
    }
}
