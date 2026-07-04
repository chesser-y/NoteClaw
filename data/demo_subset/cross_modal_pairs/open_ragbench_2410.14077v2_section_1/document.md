# Inverter Output Impedance Estimation in Power Networks: A Variable
  Direction Forgetting Recursive-Least-Square Algorithm Based Approach

Source dataset: Open-RAGBench arxiv
Query id: 852703f0-8373-43a2-a18a-eb5908ad0779
Document id: 2410.14077v2
Section id: 1

## Query
What are the challenges in estimating output impedance in inverter-based grids?

## Reference answer
Estimating output impedance in inverter-based grids is challenging due to dynamic grid conditions, which require real-time estimation. Traditional methods like signal injection and historical data analysis have limitations, such as sensitivity to noise and complexity.

## Abstract
As inverter-based loads and energy sources become increasingly prevalent,
accurate estimation of line impedance between inverters and the grid is
essential for optimizing performance and enhancing control strategies. This
paper presents a non-invasive method for estimating output-line impedance using
measurements local to the inverter. It provides a specific method for signal
conditioning of signals measured at the inverter, which makes the measured data
better suited to estimation algorithms. An algorithm based on the Variable
Direction Forgetting Recursive Least Squares (VDF-RLS) method is introduced,
which leverages these conditioned signals for precise impedance estimation. The
signal conditioning process transforms measurements into the direct-quadrature
(dq) coordinate frame, where the rotating frame frequency is determined to
facilitate a simpler and more accurate estimation. This frequency is
implemented using a secondary Phase-Locked Loop (PLL) to attenuate grid voltage
measurement variations. By isolating the variation-sensitive q-axis and relying
solely on the less sensitive d-axis, the method further minimizes the impact of
variations. The VDF-RLS estimation method achieves rapid adaptation while
ensuring stability in the absence of persistent excitation by selectively
discarding outdated data during updates. Proposed conditioning and estimation
methods are non-invasive; estimations are solely done using measured outputs,
and no signal is injected into the power network. Simulation results
demonstrate a significant improvement in impedance estimation stability,
particularly in low-excitation conditions, where the VDF-RLS method achieves
more than three time lower error compared to existing approaches such as
constant forgetting RLS and the Kalman filter.

## Matched section text
## I. INTRODUCTION

The rapid expansion of distributed energy resources (DERs) and inverter-based loads has made inverter-based grids increasingly common, driving the need for precise power regulation and deeper insights into grid interactions. In this context, output line impedance-the impedance between the inverter and the grid-plays a crucial role in determining inverter performance, affecting power injection limits and droop control characteristics [1], [2]. Improved impedance estimation, as highlighted in [3], enhances controller bandwidth, while impedance also serves as an indicator of grid stiffness and assists in islanding detection [4]. This capability supports smooth operational transitions for inverters [5]. As inverter-based resources continue to expand, accurate monitoring of these factors is essential for maintaining grid stability.

Output impedance is commonly defined as the impedance between the inverter and the grid, where the grid, in this context, represents an abstraction of the remaining network.

[^0]![img-0.jpeg](img-0.jpeg)

Fig. 1: Grid model: (a) Grid with a complex structure, and (b) Thevenin equivalent model from the inverter, where R and L represent the equivalent resistance and inductance of the Thevenin equivalent model.

In a complex power system, we model the grid as perceived by the inverter using Thevenin's theorem as an equivalent grid voltage source in series with the output line impedance (see Fig. 1). This Thevenin-equivalent impedance can vary significantly due to changes in the power network, such as fluctuations in electrical loads, the addition or removal of power sources, and environmental factors like temperature. Consequently, real-time impedance estimation is crucial for optimizing inverter performance and reliability. By continuously adapting to dynamic grid conditions, it enables stable power injection and ensures that control strategies remain effective.

The main challenges in accurately estimating output line impedance stem from several factors. (i) First, inverters typically lack access to global measurements or networkwide data, which makes it difficult to estimate the effective grid voltage. (ii) Additionally, measured signals often lack the necessary persistence of excitation, which is crucial for accurate impedance estimation. (iii) Since inverters usually operate at a steady state, only local output voltage and current are measurable, while both line impedance and grid voltage influence these measurements, making it essential to distinguish between their effects. (iv) Finally, in most grids, altering the power system to assist in impedance estimation is either impractical or not allowed. As a result, the estimation must be non-invasive, relying solely on locally measured signals without injecting real power disturbances into the system.

To address challenges (i) and (ii), many line impedance estimation methods rely on signal injection. In [6], a highfrequency signal is injected assuming that the grid voltage contains only the nominal frequency component, helping to separate line impedance from grid voltage. However, this can distort the output voltage, and tampering with power flow is

[^0]:    1 Department of Mechanical Science and Engineering, University of Illinois at Urbana-Champaign, 61801 IL, USA ${ }^{\text {a }}$ jaesang4@illinois.edu, ${ }^{\text {b }}$ askaria2@illinois.edu, ${ }^{\text {c }}$ salapaka@illinois.edu

often not allowed. In [7], the pulse-width modulation (PWM) signal used by inverters is leveraged to avoid additional distortion. However, it requires fast sensing beyond the PWM switching frequency, and filters on inverters reduce the injected signal, resulting in a low signal-to-noise ratio. In [8], a time-domain differentiation method perturbs the inverter's power, assuming constant grid voltage, with the resulting voltage and current changes attributed to line impedance. However, injection-based methods, along with concerns about voltage quality and power control, are often impractical due to grid regulations or operational constraints.

Another important class of methods addresses challenges (i), (ii), and (iv) (lack of persistent excitation while avoiding signal injection) by utilizing historical current and voltage data to estimate line impedance. These techniques leverage variations in the inverter's operating point over time. For instance, [9] assumes constant grid voltage in the direct-quadrature $(d, q)$ frame and uses a Recursive Least Squares (RLS) algorithm to estimate both line impedance and grid voltage. However, this algorithm continuously processes all data, meaning that changes in line parameters only have a noticeable impact when sustained over a long period to overcome the influence of previous data. As a result, updating the estimation to reflect new values becomes a slow process.

To speed up convergence, [4] introduces the Constant Forgetting Recursive Least Squares (CF-RLS) method, which discounts older data using a forgetting factor. While this method enhances the adaptation speed to changing parameters, the exponential discounting of historical data can lead to a loss of relevant information, which is especially significant in the absence of persistent excitation. This issue is particularly important since many inverters operate in grid-following (GFL) mode, where they track a fixed current set point that seldom changes. Thus, even aggregated historical data lacks richness for effective impedance estimation. In [10], line impedance is modeled as a dynamic state in a time-varying system defined using measured inverter voltage and current. A Kalman filter is then implemented to estimate the output line impedance. This algorithm demonstrates performance similar to the CF-RLS algorithm, sharing the same issue of gradually losing relevant information in the absence of persistent excitation.

In this work, we address challenges (i)-(iv) and also address the gaps of the above methods. We address these challenges in two steps -We first condition the measurement signals for better estimation before feeding them into the line parameter estimation algorithm. The conditioning step ensures our assumptions on grid attributes are practical and simplify the estimation process. Our approach operates in the $d-q$ coordinate frame, using a rotating frame frequency tied to the inverter rather than the grid. To generate rotating frame frequency, we design a secondary Phase Locked Loop (PLL), which is distinct from the usual PLL used for inverter control and droop regulation. This secondary PLL facilitates a coordinate frame where there is a frequency separation between current signals and grid voltage dynamics, by leveraging the algebraic structure of the constitutive equation relating
the inverter and grid voltages. In this equation, the line parameters appear as coefficients of measured current signal while the uncertainty due to grid voltage comes as an additive disturbance. Thus frequency separation simplifies the estimation problem. Unlike the inverter's primary PLL, which has a fast bandwidth to quickly track frequency changes, the secondary PLL has a lower bandwidth provides which provides better frequency separation between grid frequency changes and its phase difference variations. Additionally, we demonstrate that while the $d$-axis dynamics are less sensitive to phase difference, the $q$-axis dynamics are highly sensitive. Therefore, by focusing on the less sensitive $d$-axis dynamics, we effectively reduce fluctuations in the estimation.

In the second step, to address the issue of non-persistent excitation, we propose the use of the Variable Direction Forgetting Recursive Least Squares (VDF-RLS) method [11] for line impedance estimation. Similar to RLS and CF-RLS, VDF-RLS manages historical data using an information matrix. However, when updating the matrix with new data, VDF-RLS compares the direction of the new information vector with the singular vectors of the previous information matrix. The forgetting factor is then applied selectively, discounting only the singular values corresponding to directions aligned with the new information vector. We demonstrate that this method can estimate changing line parameters by aggregating information efficiently over time while remaining robust to noise, even when measures signals have low signal-to-noise ratio.

Upon implementation, we demonstrate that the proposed VDF-RLS-based algorithm not only tracks parameter changes rapidly when excitation is present but also remains stable, achieving significantly lower error-up to three times smaller-even in the absence of excitation. This effectively balances adaptation speed and stability. Additionally, we show that the proposed preconditioning methods efficiently reduce estimation error by mitigating measurement noise and noise induced by inverter activity.

## Linked images

- figure_1.jpg from `img-0.jpeg`
