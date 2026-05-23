pub(crate) struct ExpMovingAverage {
    alpha: f64,
    beta: f64,
    t: i32,
    st: f64,
}

impl ExpMovingAverage {
    pub fn new(alpha: f64) -> Self {
        Self {
            alpha,
            beta: 1. - alpha,
            t: 0,
            st: 0f64,
        }
    }

    pub fn update(&mut self, xt: f64) {
        self.st = self.alpha * xt + self.beta * self.st;
        self.t += 1;
    }

    pub fn avg(&self) -> f64 {
        self.st / (1. - self.beta.powi(self.t))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn round_dec(x: f64, precision: i32) -> f64 {
        let power = (10_f64).powi(precision);
        (x * power).round() / power
    }

    #[test]
    fn test_ema() {
        let mut ema = ExpMovingAverage::new(0.01);
        ema.update(10.);
        assert_eq!(round_dec(ema.avg(), 2), 10.);
        ema.update(1.);
        assert_eq!(round_dec(ema.avg(), 2), 5.48);
        ema.update(1.);
        assert_eq!(round_dec(ema.avg(), 2), 3.97);
        ema.update(1.);
        assert_eq!(round_dec(ema.avg(), 2), 3.22);
    }
}
